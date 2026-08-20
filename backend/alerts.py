"""
alerts.py
---------
All outgoing emails: price-drop alerts, signup verification codes,
and password-reset codes. Uses Gmail SMTP with an App Password.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger("alerts")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def _send(to_email: str, subject: str, body: str) -> bool:
    if not (SMTP_USER and SMTP_PASSWORD):
        logger.info("Email not configured, skipping")
        return False
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


def send_verification_email(to_email: str, code: str) -> bool:
    return _send(
        to_email,
        "Verify your PriceLens account",
        f"Your verification code is: {code}\n\nThis code expires in 10 minutes.",
    )


def send_reset_code_email(to_email: str, code: str) -> bool:
    return _send(
        to_email,
        "Reset your PriceLens password",
        f"Your password reset code is: {code}\n\nThis code expires in 10 minutes.",
    )


def send_email_alert(to_email: str, product_name: str, price: float, url: str) -> bool:
    return _send(
        to_email,
        f"Price drop: {product_name} is now Rs.{price:,.0f}",
        f"{product_name} dropped to Rs.{price:,.0f}, meeting your target price.\n\nView it here: {url}",
    )