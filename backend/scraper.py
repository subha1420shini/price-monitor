"""
Amazon/Flipkart scraping + cross-platform product matching.
Note (for viva): scraping public pages like this is common in student
projects but technically against these sites' Terms of Service. A real
production system would use official affiliate/partner APIs instead.
"""
import re
import time
import random
import logging
import difflib
from urllib.parse import urlparse

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


def polite_delay():
    time.sleep(random.uniform(1.5, 3.5))


def detect_site(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "amazon" in host:
        return "amazon"
    if "flipkart" in host:
        return "flipkart"
    raise ValueError("Only amazon.in and flipkart.com product URLs are supported")


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


def scrape_amazon(url: str) -> dict:
    polite_delay()
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

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
    return {"name": name, "price": price}


def scrape_flipkart(url: str) -> dict:
    polite_delay()
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    title_el = soup.select_one("span.VU-ZEz") or soup.select_one("span.B_NuCI")
    if title_el:
        name = title_el.get_text(strip=True)
    elif soup.title:
        name = soup.title.get_text(strip=True).split("Buy")[0].strip()
    else:
        name = "Unknown product"
    match = re.search(r'₹([\d,]+)', resp.text)
    price = _clean_price(match.group(0)) if match else None

    if price is None:
        raise ValueError("Could not find price on Flipkart page")

    return {"name": name, "price": price}
def scrape_product(url: str) -> dict:
    site = detect_site(url)
    data = scrape_amazon(url) if site == "amazon" else scrape_flipkart(url)
    data["site"] = site
    return data

def clean_title_for_search(title: str) -> str:
    noise = ["(Renewed)", "|", "-", "with", "Free", "Delivery"]
    cleaned = title
    for word in noise:
        cleaned = cleaned.replace(word, " ")
    return " ".join(cleaned.split()[:8])

CATEGORY_KEYWORDS = {
    "Electronics": ["phone", "mobile", "laptop", "earphone", "earbud", "headphone",
                    "speaker", "smartwatch", "watch", "tablet", "camera", "tv",
                    "television", "charger", "power bank", "airdopes", "buds"],
    "Fashion": ["shirt", "tshirt", "t-shirt", "jeans", "shoes", "sneakers", "dress",
                "jacket", "kurta", "saree", "footwear", "sandals", "bag", "wallet"],
    "Home & Kitchen": ["mixer", "grinder", "cookware", "kettle", "chair", "table",
                       "mattress", "pillow", "curtain", "lamp", "vacuum", "fan"],
    "Beauty & Personal Care": ["shampoo", "trimmer", "perfume", "makeup", "lotion",
                               "cream", "razor", "hair dryer"],
    "Appliances": ["refrigerator", "washing machine", "microwave", "air conditioner",
                   "ac ", "geyser", "iron"],
}


def categorize_product(name: str) -> str:
    name_lower = name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return category
    return "Other"


def scrape_flipkart(url: str) -> dict:
    polite_delay()
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title_el = soup.select_one("span.VU-ZEz") or soup.select_one("span.B_NuCI")
    if title_el:
        name = title_el.get_text(strip=True)
    elif soup.title:
        name = soup.title.get_text(strip=True).split("Buy")[0].strip()
    else:
        name = "Unknown product"

    match = re.search(r'₹([\d,]+)', resp.text)
    price = _clean_price(match.group(0)) if match else None
    if price is None:
        raise ValueError("Could not find price on Flipkart page")

    # Product image: look for the main product <img> tag (Flipkart image URLs
    # always come from rukminim1.flixcart.com, which is a reliable marker)
    image_url = None
    img_el = soup.find("img", src=re.compile(r"rukminim\d*\.flixcart\.com"))
    if img_el:
        image_url = img_el.get("src")

    return {"name": name, "price": price, "image_url": image_url, "category": categorize_product(name)}
def scrape_amazon(url: str) -> dict:
    polite_delay()
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

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

    # Product image: Amazon's main image tag has id="landingImage"
    img_el = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
    image_url = img_el.get("src") or img_el.get("data-old-hires") if img_el else None

    return {"name": name, "price": price, "image_url": image_url, "category": categorize_product(name)}

def find_cross_platform_match(source_result: dict):
    query = clean_title_for_search(source_result["name"])
    if source_result["site"] == "amazon":
        return search_flipkart(query)
    return search_amazon(query)