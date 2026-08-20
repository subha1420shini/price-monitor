"""
scraper.py
----------
Scrapes product name + price + image from Amazon, Flipkart, Meesho, Myntra,
and Purplle product pages, and can search each site for a matching product
by name (used to build cross-platform price comparisons).

Honesty note for your viva: Amazon and Myntra both use heavy bot-detection
and/or JavaScript-rendered pages, so scraping them with plain HTTP requests
is unreliable - this mirrors a real limitation of scraping without paid
APIs or browser automation (Selenium). Flipkart, Meesho, and Purplle are
more likely to return usable server-rendered HTML.
"""

import re
import time
import random
import logging
import difflib
from urllib.parse import urlparse, quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

SITES = ["amazon", "flipkart", "meesho", "myntra", "purplle"]

SEARCH_URLS = {
    "amazon": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
    "meesho": "https://www.meesho.com/search?q={q}",
    "myntra": "https://www.myntra.com/{q}",
    "purplle": "https://www.purplle.com/search?q={q}",
}

CATEGORY_KEYWORDS = {
    "Electronics": ["phone", "mobile", "laptop", "earphone", "earbud", "headphone",
                    "speaker", "smartwatch", "watch", "tablet", "camera", "tv",
                    "television", "charger", "power bank", "airdopes", "buds"],
    "Fashion": ["shirt", "tshirt", "t-shirt", "jeans", "shoes", "sneakers", "dress",
                "jacket", "kurta", "saree", "footwear", "sandals", "bag", "wallet"],
    "Home & Kitchen": ["mixer", "grinder", "cookware", "kettle", "chair", "table",
                       "mattress", "pillow", "curtain", "lamp", "vacuum", "fan"],
    "Beauty & Personal Care": ["shampoo", "trimmer", "perfume", "makeup", "lotion",
                               "cream", "razor", "hair dryer", "lipstick", "serum"],
    "Appliances": ["refrigerator", "washing machine", "microwave", "air conditioner",
                   "ac ", "geyser", "iron"],
}


def polite_delay():
    time.sleep(random.uniform(1.2, 2.5))


def detect_site(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for site in SITES:
        if site in host:
            return site
    raise ValueError("Only amazon.in, flipkart.com, meesho.com, myntra.com and purplle.com product URLs are supported")


def _clean_price(text: str):
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", text)
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def categorize_product(name: str) -> str:
    name_lower = name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return category
    return "Other"


def _fetch(url: str) -> BeautifulSoup:
    polite_delay()
    resp = requests.get(url, headers=HEADERS, timeout=12)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _generic_extract(soup: BeautifulSoup, url: str) -> dict:
    """
    Fallback extractor used for Meesho / Myntra / Purplle: takes the page
    <title> as the product name and the first rupee amount on the page as
    the price. Works reasonably well on server-rendered pages; may fail on
    heavily JavaScript-rendered pages (most likely on Myntra).
    """
    name = soup.title.get_text(strip=True) if soup.title else "Unknown product"
    name = re.split(r"[|\-–]", name)[0].strip()

    price_match = re.search(r'₹\s?([\d,]+)', str(soup))
    price = _clean_price(price_match.group(0)) if price_match else None
    if price is None:
        raise ValueError("Could not find a price on the page")

    img_el = soup.find("img", src=re.compile(r"^https?://"))
    image_url = img_el.get("src") if img_el else None

    return {"name": name, "price": price, "image_url": image_url}


def scrape_amazon(url: str) -> dict:
    soup = _fetch(url)
    title_el = soup.select_one("#productTitle")
    name = title_el.get_text(strip=True) if title_el else "Unknown product"

    price = None
    for selector in ["span.a-price span.a-offscreen", "#priceblock_ourprice", "#priceblock_dealprice"]:
        el = soup.select_one(selector)
        if el:
            price = _clean_price(el.get_text())
            if price:
                break
    if price is None:
        raise ValueError("Could not find price on Amazon page")

    img_el = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
    image_url = (img_el.get("src") or img_el.get("data-old-hires")) if img_el else None

    return {"name": name, "price": price, "image_url": image_url}


def scrape_flipkart(url: str) -> dict:
    soup = _fetch(url)
    title_el = soup.select_one("span.VU-ZEz") or soup.select_one("span.B_NuCI")
    if title_el:
        name = title_el.get_text(strip=True)
    elif soup.title:
        name = soup.title.get_text(strip=True).split("Buy")[0].strip()
    else:
        name = "Unknown product"

    match = re.search(r'₹([\d,]+)', str(soup))
    price = _clean_price(match.group(0)) if match else None
    if price is None:
        raise ValueError("Could not find price on Flipkart page")

    image_url = None
    img_el = soup.find("img", src=re.compile(r"rukminim\d*\.flixcart\.com"))
    if img_el:
        image_url = img_el.get("src")

    return {"name": name, "price": price, "image_url": image_url}


def scrape_meesho(url: str) -> dict:
    return _generic_extract(_fetch(url), url)


def scrape_myntra(url: str) -> dict:
    return _generic_extract(_fetch(url), url)


def scrape_purplle(url: str) -> dict:
    return _generic_extract(_fetch(url), url)


SCRAPERS = {
    "amazon": scrape_amazon,
    "flipkart": scrape_flipkart,
    "meesho": scrape_meesho,
    "myntra": scrape_myntra,
    "purplle": scrape_purplle,
}


def scrape_product(url: str) -> dict:
    site = detect_site(url)
    data = SCRAPERS[site](url)
    data["site"] = site
    data["category"] = categorize_product(data["name"])
    return data


def clean_title_for_search(title: str) -> str:
    noise = ["(Renewed)", "|", "-", "with", "Free", "Delivery"]
    cleaned = title
    for word in noise:
        cleaned = cleaned.replace(word, " ")
    return " ".join(cleaned.split()[:6])


def _search_generic(site: str, query: str) -> dict | None:
    """Best-effort search: fetches the site's search page and grabs the
    first plausible product link + price. Returns None if nothing usable
    is found (site blocked us, JS-rendered content, no results, etc.)."""
    try:
        url = SEARCH_URLS[site].format(q=quote(query))
        soup = _fetch(url)

        price_match = re.search(r'₹\s?([\d,]+)', str(soup))
        price = _clean_price(price_match.group(0)) if price_match else None
        if price is None:
            return None

        link_el = soup.find("a", href=re.compile(r"/(p|dp)/|/product/", re.I))
        if not link_el:
            return None
        href = link_el.get("href", "")
        product_url = href if href.startswith("http") else f"https://www.{site}.com{href}"

        name = link_el.get_text(strip=True) or query
        img_el = soup.find("img", src=re.compile(r"^https?://"))
        image_url = img_el.get("src") if img_el else None

        return {"name": name, "price": price, "url": product_url, "image_url": image_url}
    except Exception as e:
        logger.info(f"Search on {site} failed: {e}")
        return None


def find_all_platform_matches(source_result: dict) -> list[dict]:
    """
    Given a scraped product, searches every OTHER supported site for a
    matching listing. Returns a list of matches that were found (may be
    empty - not every site will have every product, and some sites resist
    scraping entirely, e.g. Myntra's JS-rendered pages).
    """
    query = clean_title_for_search(source_result["name"])
    matches = []
    for site in SITES:
        if site == source_result["site"]:
            continue
        result = _search_generic(site, query)
        if result:
            score = difflib.SequenceMatcher(None, query.lower(), result["name"].lower()).ratio()
            if score > 0.3:
                result["site"] = site
                result["category"] = categorize_product(result["name"])
                matches.append(result)
    return matches