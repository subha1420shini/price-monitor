"""
main.py
-------
Entry point wiring database, models, auth, email verification,
password reset, scraper, and scheduler into one FastAPI app.
"""

import uuid
from typing import List
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models
import schemas

from database import engine, get_db, Base

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    generate_otp,
)

from alerts import (
    send_verification_email,
    send_reset_code_email,
)

from scraper import (
    scrape_product,
    find_all_platform_matches,
)

from scheduler import start_scheduler


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="PriceLens API",
    description="Cloud-based e-commerce price monitoring and alert system",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pricelens-frontend.onrender.com",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "PriceLens Backend Running",
        "status": "online",
    }


# ============================================================
# AUTH
# ============================================================

@app.post(
    "/auth/register",
    response_model=schemas.UserOut
)
def register(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    email = payload.email.strip().lower()

    # --------------------------------------------------------
    # Check existing account
    # --------------------------------------------------------

    existing = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists"
        )

    # --------------------------------------------------------
    # Generate verification OTP
    # --------------------------------------------------------

    code = generate_otp()

    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    user = models.User(
        email=email,
        hashed_password=hash_password(payload.password),

        # User must verify email first
        is_verified=False,

        verification_code=code,

        verification_code_expiry=(
            datetime.utcnow() + timedelta(minutes=10)
        ),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # --------------------------------------------------------
    # Send verification email
    # --------------------------------------------------------

    email_sent = send_verification_email(
        email,
        code
    )

    if not email_sent:
        # Account exists but email configuration failed.
        # We keep the account so the user can resend later.
        print(
            f"WARNING: Verification email could not be sent to {email}"
        )

    return user


# ============================================================
# VERIFY EMAIL
# ============================================================

@app.post(
    "/auth/verify-email",
    response_model=schemas.Token
)
def verify_email(
    payload: schemas.VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.strip().lower()

    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email does not exist"
        )

    # --------------------------------------------------------
    # Already verified
    # --------------------------------------------------------

    if user.is_verified:
        token = create_access_token({
            "sub": user.email
        })

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    # --------------------------------------------------------
    # Check OTP
    # --------------------------------------------------------

    if (
        not user.verification_code
        or user.verification_code != payload.code
    ):
        raise HTTPException(
            status_code=400,
            detail="Incorrect verification code"
        )

    # --------------------------------------------------------
    # Check expiry
    # --------------------------------------------------------

    if (
        user.verification_code_expiry
        and datetime.utcnow() > user.verification_code_expiry
    ):
        raise HTTPException(
            status_code=400,
            detail="Verification code expired, please request a new one"
        )

    # --------------------------------------------------------
    # Verify user
    # --------------------------------------------------------

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expiry = None

    db.commit()

    # --------------------------------------------------------
    # Login automatically after verification
    # --------------------------------------------------------

    token = create_access_token({
        "sub": user.email
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ============================================================
# RESEND VERIFICATION CODE
# ============================================================

@app.post("/auth/resend-code")
def resend_code(
    payload: schemas.ResendCodeRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.strip().lower()

    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email does not exist"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Email is already verified"
        )

    # Generate new OTP

    code = generate_otp()

    user.verification_code = code

    user.verification_code_expiry = (
        datetime.utcnow() + timedelta(minutes=10)
    )

    db.commit()

    # Send email

    success = send_verification_email(
        email,
        code
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Could not send verification email"
        )

    return {
        "message": "Verification code resent successfully"
    }


# ============================================================
# LOGIN
# ============================================================

@app.post(
    "/auth/login",
    response_model=schemas.Token
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    email = form_data.username.strip().lower()

    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email does not exist"
        )

    # Check password

    if not verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    # Check verification

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )

    token = create_access_token({
        "sub": user.email
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ============================================================
# FORGOT PASSWORD
# ============================================================

@app.post("/auth/forgot-password")
def forgot_password(
    payload: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.strip().lower()

    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email does not exist"
        )

    code = generate_otp()

    user.reset_code = code

    user.reset_code_expiry = (
        datetime.utcnow() + timedelta(minutes=10)
    )

    db.commit()

    success = send_reset_code_email(
        email,
        code
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Could not send reset code"
        )

    return {
        "message": "Reset code sent to your email"
    }


# ============================================================
# RESET PASSWORD
# ============================================================

@app.post("/auth/reset-password")
def reset_password(
    payload: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.strip().lower()

    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email does not exist"
        )

    # Check code

    if (
        not user.reset_code
        or user.reset_code != payload.code
    ):
        raise HTTPException(
            status_code=400,
            detail="Incorrect reset code"
        )

    # Check expiry

    if (
        user.reset_code_expiry
        and datetime.utcnow() > user.reset_code_expiry
    ):
        raise HTTPException(
            status_code=400,
            detail="Reset code expired, please request a new one"
        )

    # Change password

    user.hashed_password = hash_password(
        payload.new_password
    )

    user.reset_code = None
    user.reset_code_expiry = None

    db.commit()

    return {
        "message": "Password reset successful"
    }


# ============================================================
# PRODUCTS
# ============================================================

@app.get(
    "/products",
    response_model=List[schemas.ProductOut]
)
def list_products(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    return (
        db.query(models.Product)
        .filter(models.Product.owner_id == user.id)
        .all()
    )


# ============================================================
# ADD PRODUCT
# ============================================================

@app.post(
    "/products",
    response_model=List[schemas.ProductOut]
)
def add_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        scraped = scrape_product(
            str(payload.url)
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read price from that URL: {e}"
        )

    group_id = str(uuid.uuid4())

    created = []

    # --------------------------------------------------------
    # Main product
    # --------------------------------------------------------

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

    # Price history

    db.add(
        models.PriceHistory(
            product_id=main_product.id,
            price=scraped["price"]
        )
    )

    db.commit()

    created.append(main_product)

    # --------------------------------------------------------
    # Cross platform matches
    # --------------------------------------------------------

    try:
        matches = find_all_platform_matches(
            scraped
        )

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

            db.add(
                models.PriceHistory(
                    product_id=twin.id,
                    price=match["price"]
                )
            )

            db.commit()

            created.append(twin)

    except Exception as e:
        print(
            f"Cross-platform matching skipped: {e}"
        )

    return created


# ============================================================
# GET PRODUCT DETAILS
# ============================================================

@app.get(
    "/products/{product_id}",
    response_model=schemas.ProductDetail
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    product = (
        db.query(models.Product)
        .filter(
            models.Product.id == product_id,
            models.Product.owner_id == user.id
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


# ============================================================
# DELETE PRODUCT
# ============================================================

@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    product = (
        db.query(models.Product)
        .filter(
            models.Product.id == product_id,
            models.Product.owner_id == user.id
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted"
    }


# ============================================================
# REFRESH PRODUCT PRICE
# ============================================================

@app.post(
    "/products/{product_id}/refresh",
    response_model=schemas.ProductOut
)
def refresh_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    product = (
        db.query(models.Product)
        .filter(
            models.Product.id == product_id,
            models.Product.owner_id == user.id
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    try:
        scraped = scrape_product(
            product.url
        )

        product.current_price = scraped["price"]

        product.last_checked = datetime.utcnow()

        db.add(
            models.PriceHistory(
                product_id=product.id,
                price=scraped["price"]
            )
        )

        db.commit()
        db.refresh(product)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not refresh product: {e}"
        )

    return product


# ============================================================
# SETTINGS
# ============================================================

@app.get(
    "/settings",
    response_model=schemas.UserOut
)
def get_settings(
    user: models.User = Depends(get_current_user)
):
    return user


@app.put(
    "/settings",
    response_model=schemas.UserOut
)
def update_settings(
    payload: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    fields = [
        "name",
        "phone",
        "age",
        "gender",
        "profile_picture_url",
        "theme_preference",
    ]

    for field in fields:

        value = getattr(
            payload,
            field
        )

        if value is not None:
            setattr(
                user,
                field,
                value
            )

    db.commit()
    db.refresh(user)

    return user


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def on_startup():
    start_scheduler()