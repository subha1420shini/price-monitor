"""
main.py
-------
Entry point wiring database, models, auth (with email verification and
password reset), scraper (multi-site), and scheduler into one FastAPI app.
"""

import uuid
from typing import List
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db, Base
from auth import hash_password, verify_password, create_access_token, get_current_user, generate_otp
from alerts import send_verification_email, send_reset_code_email
from scraper import scrape_product, find_all_platform_matches
from scheduler import start_scheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PriceLens API", description="Cloud-based e-commerce price monitoring and alert system")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ AUTH ============

@app.post("/auth/register", response_model=schemas.UserOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    code = generate_otp()
    user = models.User(
        email=email,
        hashed_password=hash_password(payload.password),
        is_verified=False,
        verification_code=code,
        verification_code_expiry=datetime.utcnow() + timedelta(minutes=10),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    send_verification_email(email, code)
    return user


@app.post("/auth/verify-email", response_model=schemas.Token)
def verify_email(payload: schemas.VerifyEmailRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email does not exist")
    if user.is_verified:
        token = create_access_token({"sub": user.email})
        return {"access_token": token, "token_type": "bearer"}
    if not user.verification_code or user.verification_code != payload.code:
        raise HTTPException(status_code=400, detail="Incorrect verification code")
    if user.verification_code_expiry and datetime.utcnow() > user.verification_code_expiry:
        raise HTTPException(status_code=400, detail="Verification code expired, please request a new one")

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expiry = None
    db.commit()

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/resend-code")
def resend_code(payload: schemas.ResendCodeRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email does not exist")
    code = generate_otp()
    user.verification_code = code
    user.verification_code_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    send_verification_email(email, code)
    return {"message": "Verification code resent"}


@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email does not exist")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before logging in")

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/forgot-password")
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email does not exist")
    code = generate_otp()
    user.reset_code = code
    user.reset_code_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    send_reset_code_email(email, code)
    return {"message": "Reset code sent to your email"}


@app.post("/auth/reset-password")
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email does not exist")
    if not user.reset_code or user.reset_code != payload.code:
        raise HTTPException(status_code=400, detail="Incorrect reset code")
    if user.reset_code_expiry and datetime.utcnow() > user.reset_code_expiry:
        raise HTTPException(status_code=400, detail="Reset code expired, please request a new one")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_code = None
    user.reset_code_expiry = None
    db.commit()
    return {"message": "Password reset successful"}


# ============ PRODUCTS ============

@app.get("/products", response_model=List[schemas.ProductOut])
def list_products(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Product).filter(models.Product.owner_id == user.id).all()


@app.post("/products", response_model=List[schemas.ProductOut])
def add_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        scraped = scrape_product(str(payload.url))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read price from that URL: {e}")

    group_id = str(uuid.uuid4())
    created = []

    main_product = models.Product(
        owner_id=user.id,
        name=scraped["name"],
        url=str(payload.url),
        site=scraped["site"],
        target_price=payload.target_price,
        current_price=scraped["price"],
        image_url=scraped.get("image_url"),
        category=scraped.get("category"),
        group_id=group_id,
        is_primary=True,
    )
    db.add(main_product)
    db.commit()
    db.refresh(main_product)
    db.add(models.PriceHistory(product_id=main_product.id, price=scraped["price"]))
    db.commit()
    created.append(main_product)

    # Best-effort: look for the same product on every other supported site.
    try:
        matches = find_all_platform_matches(scraped)
        for match in matches:
            twin = models.Product(
                owner_id=user.id,
                name=match["name"],
                url=match["url"],
                site=match["site"],
                target_price=payload.target_price,
                current_price=match["price"],
                image_url=match.get("image_url"),
                category=match.get("category"),
                group_id=group_id,
                is_primary=False,
            )
            db.add(twin)
            db.commit()
            db.refresh(twin)
            db.add(models.PriceHistory(product_id=twin.id, price=match["price"]))
            db.commit()
            created.append(twin)
    except Exception:
        pass  # cross-platform matching is a bonus feature, not critical

    return created


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
        pass
    return product


# ============ SETTINGS ============

@app.get("/settings", response_model=schemas.UserOut)
def get_settings(user: models.User = Depends(get_current_user)):
    return user


@app.put("/settings", response_model=schemas.UserOut)
def update_settings(
    payload: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    for field in ["name", "phone", "age", "gender", "profile_picture_url", "theme_preference"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


# ============ STARTUP ============

@app.on_event("startup")
def on_startup():
    start_scheduler()