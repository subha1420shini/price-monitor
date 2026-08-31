import os
import smtplib
import socket
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("alerts")

_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(
    host, port, family=0, type=0, proto=0, flags=0
):
    return _original_getaddrinfo(
        host,
        port,
        socket.AF_INET,
        type,
        proto,
        flags,
    )


socket.getaddrinfo = _ipv4_only_getaddrinfo


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def _send(to_email: str, subject: str, body: str) -> bool:

    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP_USER or SMTP_PASSWORD is missing")
        return False

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:

            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(
                SMTP_USER,
                SMTP_PASSWORD
            )

            server.sendmail(
                SMTP_USER,
                to_email,
                msg.as_string()
            )

        logger.info(
            f"Email successfully sent to {to_email}"
        )

        return True

    except Exception as e:

        logger.error(
            f"Email sending failed: {e}"
        )

        return False


def send_verification_email(
    to_email: str,
    code: str
) -> bool:

    subject = "Welcome to PriceLens — Verify Your Email"

    body = f"""
Hello,

Welcome to PriceLens!

Thank you for creating your PriceLens account.
We are happy to have you with us.

To complete your registration, please enter the
verification code below on the PriceLens website:

    {code}

This verification code will expire in 10 minutes.

If you did not create a PriceLens account, you can
safely ignore this email.

Thank you,
PriceLens Team

pricelens1248@gmail.com
"""

    return _send(
        to_email,
        subject,
        body
    )


def send_reset_code_email(
    to_email: str,
    code: str
) -> bool:

    return _send(
        to_email,
        "Reset your PriceLens password",
        f"""
Hello,

We received a request to reset your PriceLens password.

Your password reset code is:

    {code}

This code will expire in 10 minutes.

If you did not request a password reset, you can
safely ignore this email.

Regards,
PriceLens Team
"""
    )


def send_email_alert(
    to_email: str,
    product_name: str,
    price: float,
    url: str
) -> bool:

    return _send(
        to_email,
        f"Price drop: {product_name} is now Rs.{price:,.0f}",
        f"""
Hello,

Good news!

{product_name} has reached your target price.

Current price: Rs.{price:,.0f}

View the product:
{url}

Regards,
PriceLens Team
"""
    )