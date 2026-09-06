"""
main.py
-------
PriceLens FastAPI backend

Features:
- User registration
- Email OTP verification
- Resend verification OTP
- Login with JWT
- Forgot password OTP
- Reset password
- Product tracking
- Cross-platform price matching
- Price history
- Dashboard data
- User settings
- Profile picture
- Scheduler
"""

import uuid
from typing import List
from datetime import datetime, timedelta

from dotenv import load_dotenv

# ------------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES FIRST
# ------------------------------------------------------------

load_dotenv()


# ------------------------------------------------------------
# FASTAPI
# ------------------------------------------------------------

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    BackgroundTasks,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm


# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------

from sqlalchemy.orm import Session

import models
import schemas

from database import (
    engine,
    get_db,
    Base,
)


# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    generate_otp,
)


# ------------------------------------------------------------
# EMAIL
# ------------------------------------------------------------

from alerts import (
    send_verification_email,
    send_reset_code_email,
)


# ------------------------------------------------------------
# SCRAPER
# ------------------------------------------------------------

from scraper import (
    scrape_product,
    find_all_platform_matches,
)


# ------------------------------------------------------------
# SCHEDULER
# ------------------------------------------------------------

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
    description=(
        "Cloud-based e-commerce price monitoring "
        "and alert system"
    ),
    version="1.0.0",
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
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "PriceLens API",
    }


# ============================================================
# AUTH
# ============================================================


# ============================================================
# REGISTER
# ============================================================

@app.post(
    "/auth/register",
    response_model=schemas.UserOut,
)
def register(
    payload: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Clean email
    # --------------------------------------------------------

    email = payload.email.strip().lower()


    # --------------------------------------------------------
    # Check existing account
    # --------------------------------------------------------

    existing = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )


    if existing:

        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists",
        )


    # --------------------------------------------------------
    # Generate OTP
    # --------------------------------------------------------

    code = generate_otp()


    # --------------------------------------------------------
    # OTP expiry
    # --------------------------------------------------------

    expiry = (
        datetime.utcnow()
        + timedelta(minutes=10)
    )


    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    user = models.User(

        email=email,

        hashed_password=
            hash_password(
                payload.password
            ),

        is_verified=False,

        verification_code=code,

        verification_code_expiry=expiry,

    )


    db.add(user)

    db.commit()

    db.refresh(user)


    # --------------------------------------------------------
    # SEND EMAIL IN BACKGROUND
    #
    # IMPORTANT:
    # This prevents register API from hanging while
    # SMTP/email service is slow.
    # --------------------------------------------------------

    background_tasks.add_task(
        send_verification_email,
        email,
        code,
    )


    # --------------------------------------------------------
    # Server log
    # --------------------------------------------------------

    print(
        f"Registration successful for {email}"
    )

    print(
        f"Verification OTP for {email}: {code}"
    )


    # --------------------------------------------------------
    # Return immediately
    # --------------------------------------------------------

    return user


# ============================================================
# VERIFY EMAIL
# ============================================================

@app.post(
    "/auth/verify-email",
    response_model=schemas.Token,
)
def verify_email(
    payload: schemas.VerifyEmailRequest,
    db: Session = Depends(get_db),
):

    email = payload.email.strip().lower()


    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=400,
            detail="Email does not exist",
        )


    # --------------------------------------------------------
    # Already verified
    # --------------------------------------------------------

    if user.is_verified:

        token = create_access_token(
            {
                "sub": user.email
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer",
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
            detail="Incorrect verification code",
        )


    # --------------------------------------------------------
    # Check expiry
    # --------------------------------------------------------

    if (
        user.verification_code_expiry
        and datetime.utcnow()
        > user.verification_code_expiry
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Verification code expired. "
                "Please request a new one."
            ),
        )


    # --------------------------------------------------------
    # Verify account
    # --------------------------------------------------------

    user.is_verified = True

    user.verification_code = None

    user.verification_code_expiry = None


    db.commit()

    db.refresh(user)


    # --------------------------------------------------------
    # Create JWT
    # --------------------------------------------------------

    token = create_access_token(
        {
            "sub": user.email
        }
    )


    return {
        "access_token": token,
        "token_type": "bearer",
    }


# ============================================================
# RESEND VERIFICATION CODE
# ============================================================

@app.post("/auth/resend-code")
def resend_code(
    payload: schemas.ResendCodeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):

    email = payload.email.strip().lower()


    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=400,
            detail="Email does not exist",
        )


    # --------------------------------------------------------
    # Already verified
    # --------------------------------------------------------

    if user.is_verified:

        raise HTTPException(
            status_code=400,
            detail="Email is already verified",
        )


    # --------------------------------------------------------
    # Generate new OTP
    # --------------------------------------------------------

    code = generate_otp()


    user.verification_code = code

    user.verification_code_expiry = (
        datetime.utcnow()
        + timedelta(minutes=10)
    )


    db.commit()


    # --------------------------------------------------------
    # Send in background
    # --------------------------------------------------------

    background_tasks.add_task(
        send_verification_email,
        email,
        code,
    )


    print(
        f"New verification OTP for {email}: {code}"
    )


    return {
        "message": (
            "Verification code sent successfully"
        )
    }


# ============================================================
# LOGIN
# ============================================================

@app.post(
    "/auth/login",
    response_model=schemas.Token,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    email = (
        form_data.username
        .strip()
        .lower()
    )


    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email does not exist",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


    # --------------------------------------------------------
    # Verify password
    # --------------------------------------------------------

    if not verify_password(
        form_data.password,
        user.hashed_password,
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


    # --------------------------------------------------------
    # Check email verification
    # --------------------------------------------------------

    if not user.is_verified:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Please verify your email "
                "before logging in"
            ),
        )


    # --------------------------------------------------------
    # Create JWT
    # --------------------------------------------------------

    token = create_access_token(
        {
            "sub": user.email
        }
    )


    return {
        "access_token": token,
        "token_type": "bearer",
    }


# ============================================================
# FORGOT PASSWORD
# ============================================================

@app.post("/auth/forgot-password")
def forgot_password(
    payload: schemas.ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):

    email = payload.email.strip().lower()


    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=400,
            detail="Email does not exist",
        )


    # --------------------------------------------------------
    # Generate reset OTP
    # --------------------------------------------------------

    code = generate_otp()


    user.reset_code = code

    user.reset_code_expiry = (
        datetime.utcnow()
        + timedelta(minutes=10)
    )


    db.commit()


    # --------------------------------------------------------
    # Send email in background
    # --------------------------------------------------------

    background_tasks.add_task(
        send_reset_code_email,
        email,
        code,
    )


    print(
        f"Password reset OTP for {email}: {code}"
    )


    return {
        "message": (
            "Reset code sent to your email"
        )
    }


# ============================================================
# RESET PASSWORD
# ============================================================

@app.post("/auth/reset-password")
def reset_password(
    payload: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db),
):

    email = payload.email.strip().lower()


    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=400,
            detail="Email does not exist",
        )


    # --------------------------------------------------------
    # Check OTP
    # --------------------------------------------------------

    if (
        not user.reset_code
        or user.reset_code != payload.code
    ):

        raise HTTPException(
            status_code=400,
            detail="Incorrect reset code",
        )


    # --------------------------------------------------------
    # Check expiry
    # --------------------------------------------------------

    if (
        user.reset_code_expiry
        and datetime.utcnow()
        > user.reset_code_expiry
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Reset code expired. "
                "Please request a new one."
            ),
        )


    # --------------------------------------------------------
    # Update password
    # --------------------------------------------------------

    user.hashed_password = hash_password(
        payload.new_password
    )


    user.reset_code = None

    user.reset_code_expiry = None


    db.commit()


    return {
        "message": (
            "Password reset successful"
        )
    }



# ============================================================
# PRODUCT CATEGORY DETECTOR
# ============================================================

def detect_category(product_name: str) -> str:
    name = (product_name or "").strip().lower()

    rules = {
        "Mobiles & Accessories": [
            "smartphone", "mobile phone", "mobile", "iphone", "ipad",
            "oneplus", "samsung galaxy", "redmi", "realme", "vivo",
            "oppo", "pixel", "phone case", "mobile cover", "charger",
            "power bank", "screen protector"
        ],
        "Laptops & Computers": [
            "laptop", "notebook", "macbook", "chromebook", "desktop",
            "computer", "monitor", "keyboard", "mouse", "webcam",
            "ssd", "hard disk", "ram", "graphics card", "gpu",
            "printer", "router"
        ],
        "Audio & Headphones": [
            "headphone", "headset", "earphone", "earbud", "airpods",
            "speaker", "soundbar", "microphone"
        ],
        "Cameras & Accessories": [
            "camera", "dslr", "mirrorless", "action camera", "camcorder",
            "lens", "tripod", "camera bag"
        ],
        "Gaming": [
            "gaming", "playstation", "ps5", "ps4", "xbox", "nintendo",
            "controller", "gamepad", "video game"
        ],
        "Beauty & Makeup": [
            "makeup", "lipstick", "foundation", "concealer", "mascara",
            "eyeliner", "blush", "cosmetic", "perfume", "fragrance",
            "nail polish"
        ],
        "Skincare": [
            "skincare", "skin care", "face wash", "cleanser", "serum",
            "moisturizer", "moisturiser", "sunscreen", "face cream",
            "toner", "scrub", "face mask"
        ],
        "Hair Care": [
            "shampoo", "conditioner", "hair oil", "hair serum", "hair mask",
            "hair dryer", "straightener", "hair curler", "trimmer"
        ],
        "Shoes & Footwear": [
            "shoe", "shoes", "sneaker", "sandals", "slipper",
            "flip flop", "boots", "heels", "loafers", "footwear"
        ],
        "Bags & Accessories": [
            "bag", "backpack", "handbag", "wallet", "purse", "sling bag",
            "belt", "sunglasses", "accessory", "accessories"
        ],
        "Jewellery": [
            "jewellery", "jewelry", "necklace", "earring", "bracelet",
            "bangle", "ring", "chain", "pendant"
        ],
        "Watches": ["watch", "watches", "smartwatch", "smart watch"],
        "Fashion & Clothing": [
            "shirt", "t-shirt", "tshirt", "jeans", "trouser", "pant",
            "dress", "kurti", "saree", "sari", "top", "jacket", "coat",
            "hoodie", "sweater", "shorts", "skirt", "clothing", "fashion",
            "ethnic wear", "western wear"
        ],
        "Kitchen Appliances": [
            "mixer", "grinder", "mixer grinder", "air fryer", "microwave",
            "oven", "toaster", "kettle", "induction", "rice cooker",
            "blender", "juicer", "dishwasher", "refrigerator", "fridge"
        ],
        "Furniture": [
            "sofa", "chair", "table", "bed", "mattress", "wardrobe",
            "cabinet", "bookshelf", "furniture", "dining table"
        ],
        "Home Decor": [
            "home decor", "decoration", "curtain", "carpet", "rug",
            "wall art", "painting", "showpiece", "lamp", "cushion", "vase"
        ],
        "Home & Kitchen": [
            "kitchen", "cookware", "utensil", "pan", "pot", "pressure cooker",
            "bottle", "storage", "cleaning", "vacuum cleaner", "home appliance"
        ],
        "Books & Education": [
            "book", "books", "novel", "textbook", "notebook", "study",
            "education", "stationery", "pen", "pencil", "exam"
        ],
        "Toys & Kids": [
            "toy", "toys", "kids", "kid", "children", "doll", "lego",
            "puzzle", "remote control car", "teddy"
        ],
        "Baby Products": [
            "baby", "diaper", "nappy", "feeding bottle", "baby food",
            "baby stroller", "baby care", "infant", "newborn"
        ],
        "Fitness & Sports": [
            "fitness", "gym", "yoga", "dumbbell", "treadmill", "exercise",
            "sports", "cricket", "football", "badminton", "basketball",
            "running", "cycle", "bicycle", "fitness band"
        ],
        "Pet Supplies": [
            "pet", "dog food", "cat food", "pet food", "dog", "cat",
            "pet toy", "pet bed", "leash", "aquarium"
        ],
        "Travel Accessories": [
            "travel", "luggage", "suitcase", "trolley bag", "travel bag",
            "passport holder", "neck pillow", "travel adapter"
        ],
        "Car & Bike Accessories": [
            "car accessories", "bike accessories", "motorcycle", "scooter",
            "helmet", "car cover", "bike cover", "dashcam", "tyre",
            "automotive", "car", "bike"
        ],
        "Grocery & Daily Essentials": [
            "grocery", "rice", "wheat", "flour", "dal", "oil", "sugar",
            "salt", "snacks", "biscuit", "coffee", "tea", "soap",
            "detergent", "toothpaste", "toothbrush", "household"
        ],
        "Gifts": ["gift", "gifts", "gift set", "gift box", "hamper"],
        "Electronics": [
            "electronics", "television", "led tv", "smart tv",
            "tablet", "power adapter", "cable", "usb", "smart device"
        ],
    }

    for category, keywords in rules.items():
        if any(keyword in name for keyword in keywords):
            return category

    return "Others"


# ============================================================
# PRODUCTS
# ============================================================


# ============================================================
# GET ALL PRODUCTS
# ============================================================

@app.get(
    "/products",
    response_model=List[schemas.ProductOut],
)
def list_products(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):

    products = (
        db.query(models.Product)
        .filter(
            models.Product.owner_id == user.id
        )
        .order_by(
            models.Product.created_at.desc()
        )
        .all()
    )

    # Automatically categorize old products too.
    changed = False

    for product in products:
        if not product.category or product.category == "Other":
            product.category = detect_category(product.name)
            changed = True

    if changed:
        db.commit()

    return products


# ============================================================
# ADD PRODUCT
# ============================================================

@app.post(
    "/products",
    response_model=List[schemas.ProductOut],
)
def add_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Scrape main product
    # --------------------------------------------------------

    try:

        scraped = scrape_product(
            str(payload.url)
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not read price from that URL: "
                f"{e}"
            ),
        )


    # --------------------------------------------------------
    # Group ID
    # --------------------------------------------------------

    group_id = str(uuid.uuid4())


    created = []


    # ========================================================
    # MAIN PRODUCT
    # ========================================================

    main_product = models.Product(

        owner_id=user.id,

        name=scraped["name"],

        url=str(payload.url),

        site=scraped["site"],

        target_price=payload.target_price,

        current_price=scraped["price"],

        image_url=scraped.get("image_url"),

        category=detect_category(scraped.get("name", "")),

        group_id=group_id,

        is_primary=True,

        is_active=True,

        last_checked=datetime.utcnow(),

    )


    db.add(main_product)

    db.commit()

    db.refresh(main_product)


    # --------------------------------------------------------
    # Price history
    # --------------------------------------------------------

    history = models.PriceHistory(

        product_id=main_product.id,

        price=scraped["price"],

        checked_at=datetime.utcnow(),

    )


    db.add(history)

    db.commit()


    created.append(main_product)


    # ========================================================
    # CROSS PLATFORM MATCHES
    # ========================================================

    try:

        matches = find_all_platform_matches(
            scraped
        )


        for match in matches:

            # ----------------------------------------------
            # Avoid invalid match
            # ----------------------------------------------

            if not match.get("url"):
                continue

            if match.get("price") is None:
                continue


            # ----------------------------------------------
            # Create twin product
            # ----------------------------------------------

            twin = models.Product(

                owner_id=user.id,

                name=match["name"],

                url=match["url"],

                site=match["site"],

                target_price=payload.target_price,

                current_price=match["price"],

                image_url=match.get("image_url"),

                category=detect_category(match.get("name", scraped.get("name", ""))),

                group_id=group_id,

                is_primary=False,

                is_active=True,

                last_checked=datetime.utcnow(),

            )


            db.add(twin)

            db.commit()

            db.refresh(twin)


            # ----------------------------------------------
            # Price history
            # ----------------------------------------------

            db.add(
                models.PriceHistory(

                    product_id=twin.id,

                    price=match["price"],

                    checked_at=datetime.utcnow(),

                )
            )


            db.commit()


            created.append(twin)


    except Exception as e:

        print(
            "Cross-platform matching skipped:",
            e,
        )


    return created


# ============================================================
# GET PRODUCT DETAILS
# ============================================================

@app.get(
    "/products/{product_id}",
    response_model=schemas.ProductDetail,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):

    product = (
        db.query(models.Product)
        .filter(
            models.Product.id == product_id,
            models.Product.owner_id == user.id,
        )
        .first()
    )


    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )


    return product


# ============================================================
# DELETE PRODUCT
# ============================================================

@app.delete(
    "/products/{product_id}"
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):

    product = (
        db.query(models.Product)
        .filter(
            models.Product.id == product_id,
            models.Product.owner_id == user.id,
        )
        .first()
    )


    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found",
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
    response_model=schemas.ProductOut,
)
def refresh_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):

    product = (
        db.query(models.Product)
        .filter(
            models.Product.id == product_id,
            models.Product.owner_id == user.id,
        )
        .first()
    )


    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )


    try:

        scraped = scrape_product(
            product.url
        )


        product.current_price = (
            scraped["price"]
        )


        product.last_checked = (
            datetime.utcnow()
        )


        db.add(
            models.PriceHistory(

                product_id=product.id,

                price=scraped["price"],

                checked_at=datetime.utcnow(),

            )
        )


        db.commit()

        db.refresh(product)


    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not refresh product: {e}"
            ),
        )


    return product


# ============================================================
# SETTINGS
# ============================================================


# ============================================================
# GET SETTINGS
# ============================================================

@app.get(
    "/settings",
    response_model=schemas.UserOut,
)
def get_settings(
    user: models.User = Depends(get_current_user),
):

    return user


# ============================================================
# UPDATE SETTINGS
# ============================================================

@app.put(
    "/settings",
    response_model=schemas.UserOut,
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
            field,
            None,
        )


        if value is not None:

            setattr(
                user,
                field,
                value,
            )


    db.commit()

    db.refresh(user)


    return user


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def on_startup():

    print(
        "========================================"
    )

    print(
        "PriceLens API starting..."
    )

    print(
        "Database connected"
    )

    print(
        "========================================"
    )


    try:

        start_scheduler()

        print(
            "Price monitoring scheduler started"
        )

    except Exception as e:

        print(
            "Scheduler could not start:",
            e,
        )


# ============================================================
# END
# ============================================================