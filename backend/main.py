import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import (
    CLOTHES_DIR,
    CROPS_DIR,
    DATA_DIR,
    PRODUCTS_FILE,
    WARDROBE_FILE,
    FEEDBACK_FILE,
    CATEGORIES,
    RETAILERS,
    EMBEDDING_MODEL_NAME,
    DEVICE
)
from backend.services.wardrobe_service import WardrobeService
from backend.services.recommend_service import RecommendationService
from backend.services.scraper_service import ScraperService

app = FastAPI(
    title="Fashion-2 AI Stylist & Recommendation Engine",
    description="Personal AI fashion recommendation system powered by Fashion-CLIP, SAM/U2Net segmentation, FAISS vector search, and active preference learning.",
    version="2.0.0"
)

# Enable CORS for Vite frontend (http://localhost:5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folders for images
app.mount("/api/static/crops", StaticFiles(directory=str(CROPS_DIR)), name="crops")
app.mount("/api/static/clothes", StaticFiles(directory=str(CLOTHES_DIR)), name="clothes")

# Initialize core services
wardrobe_service = WardrobeService()
recommend_service = RecommendationService(wardrobe_service)
scraper_service = ScraperService(wardrobe_service.embedder, recommend_service.vector_store)

# Initialize catalog on startup
@app.on_event("startup")
def startup_event():
    print("[Startup] Initializing Fashion-2 Backend Services...")
    # Initialize catalog and index if not present
    scraper_service.initialize_or_refresh_catalog(force_reseed=False)
    # Scan wardrobe photos
    wardrobe_service.scan_and_process(force_resegment=False)
    print("[Startup] Ready! Wardrobe & Catalog initialized.")

# Request Models
class FeedbackRequest(BaseModel):
    product_id: str
    is_like: bool
    product_data: Optional[Dict[str, Any]] = None

class RecommendRequest(BaseModel):
    garment_id: Optional[str] = "all"
    category: Optional[str] = "all"
    retailer: Optional[str] = "all"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    size: Optional[str] = "all"
    sort_by: Optional[str] = "relevance"
    preference_weight: Optional[float] = 0.25
    top_k: Optional[int] = 40

class ScrapeRequest(BaseModel):
    category: Optional[str] = "tops"
    retailer: Optional[str] = "all"

# REST Endpoints
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Fashion-2 Engine",
        "wardrobe_count": len(wardrobe_service.wardrobe_data.get("items", [])),
        "catalog_count": len(recommend_service.vector_store.products),
        "index_ready": recommend_service.vector_store.index is not None and recommend_service.vector_store.index.ntotal > 0,
        "likes_count": len(recommend_service.feedback.get("likes", {})),
        "dislikes_count": len(recommend_service.feedback.get("dislikes", {}))
    }

@app.get("/api/wardrobe")
def get_wardrobe():
    """Retrieve all detected and cropped garments from user's wardrobe."""
    items = wardrobe_service.get_items_summary()
    return {
        "total": len(items),
        "has_style_profile": wardrobe_service.wardrobe_data.get("style_profile") is not None,
        "items": items
    }

@app.post("/api/wardrobe/rescan")
def rescan_wardrobe(force: bool = Query(False, description="Force re-segmentation of all images")):
    """Rescans the clothes/ folder, detects garments, and triggers live scraping for new items."""
    result = wardrobe_service.scan_and_process(force_resegment=force)
    new_items = result.get("new_items", [])
    if new_items:
        scraper_service.scrape_and_index_for_new_garments(new_items, limit_per_item=30)
        
    return {
        "status": "success",
        "message": f"Wardrobe refreshed. Found {result['total_garments']} garments ({result.get('new_items_count', 0)} new).",
        "new_items_count": result.get("new_items_count", 0),
        "background_scraping": len(new_items) > 0,
        "data": result
    }

@app.get("/api/catalog/status")
def get_catalog_status():
    return {
        "is_indexing": scraper_service.is_indexing(),
        "total_products": len(recommend_service.vector_store.products),
        "index_size": recommend_service.vector_store.index.ntotal if recommend_service.vector_store.index else 0
    }

@app.post("/api/recommend")
def get_recommendations(req: RecommendRequest):
    """
    Search catalog with nearest-neighbor Fashion-CLIP similarity,
    multi-attribute metadata filters, and personalized preference reranking.
    """
    return recommend_service.recommend(
        garment_id=req.garment_id,
        category=req.category,
        retailer=req.retailer,
        min_price=req.min_price,
        max_price=req.max_price,
        size=req.size,
        sort_by=req.sort_by or "relevance",
        preference_weight=req.preference_weight or 0.25,
        top_k=req.top_k or 40
    )

@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    """
    Record thumbs up or thumbs down for a product.
    Immediately updates the preference vector for personalized reranking.
    """
    return recommend_service.record_feedback(
        product_id=req.product_id,
        is_like=req.is_like,
        product_data=req.product_data
    )

@app.get("/api/catalog")
def get_catalog(
    category: Optional[str] = "all",
    retailer: Optional[str] = "all",
    limit: int = Query(60, ge=1, le=300),
    offset: int = Query(0, ge=0)
):
    """Explore raw catalog items."""
    products = recommend_service.vector_store.products
    filtered = []
    for p in products:
        if category != "all" and p.get("category") != category.lower():
            continue
        if retailer != "all" and p.get("retailer") != retailer:
            continue
        filtered.append({k: v for k, v in p.items() if k != "embedding"})

    return {
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
        "items": filtered[offset:offset + limit]
    }

@app.post("/api/catalog/scrape")
def trigger_scrape(req: ScrapeRequest):
    """Run an on-demand scraper or re-index."""
    return scraper_service.run_live_category_scrape(
        category=req.category or "tops",
        retailer=req.retailer or "all"
    )

@app.get("/api/style-insights")
def get_style_insights():
    """Retrieve comprehensive style analysis, color palettes, and taste analytics."""
    return recommend_service.get_style_insights()

@app.get("/api/likes")
def get_liked_products():
    """Retrieve full product objects for all liked dresses/items."""
    return recommend_service.get_liked_products()


@app.get("/api/meta")
def get_metadata():
    """Get metadata categories, retailers, sizes, price ranges."""
    products = recommend_service.vector_store.products
    prices = [p.get("price", 0) for p in products if p.get("price")]
    min_p = min(prices) if prices else 0
    max_p = max(prices) if prices else 15000

    return {
        "categories": ["all"] + CATEGORIES,
        "retailers": ["all"] + RETAILERS,
        "sizes": ["all", "XS", "S", "M", "L", "XL", "XXL", "26", "28", "30", "32", "34", "36", "37", "38", "39", "40", "Free Size"],
        "price_bounds": {
            "min": int(min_p),
            "max": int(max_p)
        },
        "sort_options": [
            {"id": "relevance", "label": "AI Relevance & Style Match"},
            {"id": "price_asc", "label": "Price: Low to High"},
            {"id": "price_desc", "label": "Price: High to Low"},
            {"id": "discount", "label": "Highest Discount"}
        ]
    }
