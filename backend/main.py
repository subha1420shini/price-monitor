"""
main.py
-------
This is the entry point of the backend. It wires together the database,
models, auth, scraper, and scheduler into one FastAPI application with
these endpoints:

  POST /auth/register        -> create a new user
  POST /auth/login           -> log in, get a JWT token
  GET  /products              -> list all products the logged-in user tracks
  POST /products               -> add a new product to track (scrapes it immediately,
                                   and tries to find + track the matching product
                                   on the other platform)
  GET  /products/{id}         -> get one product's full details + price history
  DELETE /products/{id}       -> stop tracking a product
  POST /products/{id}/refresh -> re-scrape a single product right now
  GET  /settings               -> get the logged-in user's profile
  PUT  /settings               -> update the logged-in user's profile

Run this with: uvicorn main:app --reload
Then open http://127.0.0.1:8000/docs to test everything interactively.
"""

from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
import models
import schemas
from database import engine, get_db, Base
from auth import hash_password, verify_password, create_access_token, get_current_user
from scraper import scrape_product, find_cross_platform_match
from scheduler import start_scheduler

# Creates all tables in the database if they don't already exist.
# (For a real production app you'd use Alembic migrations instead, but for
# a final-year project this "create on startup" approach is perfectly fine.)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PriceWatch API", description="Cloud-based e-commerce price monitoring and alert system")

# Allows the frontend (running on a different port, e.g. localhost:5500)
# to call this API from the browser. In production, replace "*" with your
# actual frontend domain for better security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ AUTH ROUTES ============

@app.post("/auth/register", response_model=schemas.UserOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = models.User(email=email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


# ============ PRODUCT ROUTES ============

@app.get("/products", response_model=List[schemas.ProductOut])
def list_products(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Product).filter(models.Product.owner_id == user.id).all()


@app.post("/products", response_model=schemas.ProductDetail)
def add_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        scraped = scrape_product(str(payload.url))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read price from that URL: {e}")

    product = models.Product(
        owner_id=user.id,
        name=scraped["name"],
        url=str(payload.url),
        site=scraped["site"],
        target_price=payload.target_price,
        current_price=scraped["price"],
        image_url=scraped.get("image_url"),
        category=scraped.get("category"),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    db.add(models.PriceHistory(product_id=product.id, price=scraped["price"]))
    db.commit()

    # Try to find and track the same product on the other platform.
    # If this fails for any reason, we don't want it to break adding the
    # original product - so it's wrapped in its own try/except.
    try:
        match = find_cross_platform_match(scraped)
        if match and match.get("price"):
            twin_site = "flipkart" if scraped["site"] == "amazon" else "amazon"
            twin = models.Product(
                owner_id=user.id,
                name=match["name"],
                url=match["url"],
                site=twin_site,
                target_price=payload.target_price,
                current_price=match["price"],
                image_url=match.get("image_url"),
                category=match.get("category"),
            )
            db.add(twin)
            db.commit()
            db.refresh(twin)
            db.add(models.PriceHistory(product_id=twin.id, price=match["price"]))

            product.matched_product_id = twin.id
            twin.matched_product_id = product.id
            db.commit()
            db.refresh(product)
    except Exception:
        pass  # cross-platform match is a bonus feature, not critical

    return product


@app.get("/products/{product_id}", response_model=schemas.ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id, models.Product.owner_id == user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id, models.Product.owner_id == user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}


@app.post("/products/{product_id}/refresh", response_model=schemas.ProductOut)
def refresh_product(product_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id, models.Product.owner_id == user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        scraped = scrape_product(product.url)
        product.current_price = scraped["price"]
        product.last_checked = datetime.utcnow()
        db.add(models.PriceHistory(product_id=product.id, price=scraped["price"]))
        db.commit()
        db.refresh(product)
    except Exception:
        pass  # if the live site is unreachable, just show the last known price

    return product


# ============ SETTINGS ROUTES ============

@app.get("/settings", response_model=schemas.UserOut)
def get_settings(user: models.User = Depends(get_current_user)):
    return user


@app.put("/settings", response_model=schemas.UserOut)
def update_settings(
    payload: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if payload.name is not None:
        user.name = payload.name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.age is not None:
        user.age = payload.age
    if payload.profile_picture_url is not None:
        user.profile_picture_url = payload.profile_picture_url
    db.commit()
    db.refresh(user)
    return user


# ============ STARTUP ============

@app.on_event("startup")
def on_startup():
    # Starts the background scheduler that re-checks all tracked products
    # every hour, for as long as this server keeps running.
    start_scheduler()