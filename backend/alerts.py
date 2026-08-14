"""Email + Telegram alerts. Both optional — skipped if env vars not set."""
import os
import smtplib
import logging
from email.mime.text import MIMEText
import requests

logger = logging.getLogger("alerts")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def send_email_alert(to_email: str, product_name: str, price: float, url: str) -> bool:
    if not (SMTP_USER and SMTP_PASSWORD):
        logger.info("Email not configured, skipping")
        return False
    subject = f"Price drop: {product_name} is now Rs.{price:,.0f}"
    body = f"{product_name} dropped to Rs.{price:,.0f}\n{url}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


def send_telegram_alert(chat_id: str, product_name: str, price: float, url: str) -> bool:
    if not (TELEGRAM_BOT_TOKEN and chat_id):
        logger.info("Telegram not configured, skipping")
        return False
    text = f"Price drop!\n{product_name}\nRs.{price:,.0f}\n{url}"
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(api_url, data={"chat_id": chat_id, "text": text}, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram failed: {e}")
        return False