"""
scheduler.py
------------
Every hour, re-checks every active product's price, updates history, and
sends an email alert to the owner if the price has reached their target.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from database import SessionLocal
import models
from scraper import scrape_product
from alerts import send_email_alert

logger = logging.getLogger("scheduler")


def check_all_products():
    db: Session = SessionLocal()
    try:
        products = db.query(models.Product).filter(models.Product.is_active == True).all()
        logger.info(f"Checking {len(products)} products")

        for product in products:
            try:
                result = scrape_product(product.url)
                new_price = result["price"]
                product.current_price = new_price
                product.last_checked = datetime.utcnow()
                db.add(models.PriceHistory(product_id=product.id, price=new_price))

                if new_price <= product.target_price:
                    owner = db.query(models.User).filter(models.User.id == product.owner_id).first()
                    if owner:
                        if send_email_alert(owner.email, f"{product.name} ({product.site})", new_price, product.url):
                            db.add(models.Alert(product_id=product.id, price_at_alert=new_price, channel="email"))
                db.commit()
            except Exception as e:
                logger.error(f"Failed on product {product.id}: {e}")
                db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_products, "interval", hours=1, id="price_check", next_run_time=datetime.utcnow())
    scheduler.start()
    logger.info("Scheduler started - checking every hour")
    return scheduler