import os
from pathlib import Path

# Allow multiple OpenMP initializations to prevent runtime crashes
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

BASE_DIR = Path(__file__).resolve().parent.parent
CLOTHES_DIR = BASE_DIR / "clothes"
CROPS_DIR = BASE_DIR / "crops"
DATA_DIR = BASE_DIR / "data"

PRODUCTS_FILE = DATA_DIR / "products.json"
CATALOG_INDEX_FILE = DATA_DIR / "catalog.index"
WARDROBE_FILE = DATA_DIR / "wardrobe.json"
FEEDBACK_FILE = DATA_DIR / "feedback.json"
SCRAPER_LOG_FILE = DATA_DIR / "scraper_cron.log"

# Create required directories
CLOTHES_DIR.mkdir(parents=True, exist_ok=True)
CROPS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Categories
CATEGORIES = [
    "tops",
    "dresses",
    "bottoms",
    "ethnic",
    "footwear"
]

RETAILERS = [
    "Ajio",
    "Myntra",
    "Max Fashion"
]

# Model configuration
EMBEDDING_MODEL_NAME = "openai/clip-vit-base-patch32"
EMBEDDING_DIM = 512
DEVICE = "cpu"
