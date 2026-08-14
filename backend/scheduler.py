"""Background job: every 6 hours, re-check every tracked product's price."""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from database import SessionLocal
import models
from scraper import scrape_product
from alerts import send_email_alert, send_telegram_alert

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

                cheapest_price = new_price
                cheapest_product = product
                if product.matched_product_id:
                    twin = db.query(models.Product).get(product.matched_product_id)
                    if twin and twin.current_price and twin.current_price < cheapest_price:
                        cheapest_price = twin.current_price
                        cheapest_product = twin

                if cheapest_price <= product.target_price:
                    owner = db.query(models.User).filter(models.User.id == product.owner_id).first()
                    if owner:
                        if send_email_alert(owner.email, f"{cheapest_product.name} ({cheapest_product.site})", cheapest_price, cheapest_product.url):
                            db.add(models.Alert(product_id=cheapest_product.id, price_at_alert=cheapest_price, channel="email"))
                        if owner.telegram_chat_id:
                            if send_telegram_alert(owner.telegram_chat_id, cheapest_product.name, cheapest_price, cheapest_product.url):
                                db.add(models.Alert(product_id=cheapest_product.id, price_at_alert=cheapest_price, channel="telegram"))
                db.commit()
            except Exception as e:
                logger.error(f"Failed on product {product.id}: {e}")
                db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_products, "interval", hours=6, id="price_check", next_run_time=datetime.utcnow())
    scheduler.start()
    logger.info("Scheduler started — checking every 6 hours")
    return scheduler