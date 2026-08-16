import os
import time
import json
import datetime
import threading
import requests
from io import BytesIO
from PIL import Image
from typing import List, Dict, Any
import numpy as np

from backend.config import PRODUCTS_FILE, SCRAPER_LOG_FILE, EMBEDDING_DIM
from backend.models.embedder import FashionEmbedder
from backend.models.vector_store import CatalogVectorStore
from backend.scrapers.seed_catalog import get_curated_retailer_catalog
from backend.scrapers.ajio import AjioScraper
from backend.scrapers.myntra import MyntraScraper
from backend.scrapers.max_fashion import MaxFashionScraper

class ScraperService:
    def __init__(self, embedder: FashionEmbedder, vector_store: CatalogVectorStore):
        self.embedder = embedder
        self.vector_store = vector_store
        self.ajio = AjioScraper()
        self.myntra = MyntraScraper()
        self.max_fashion = MaxFashionScraper()
        self._is_indexing = False
        self._indexing_thread = None

    def log_scrape_event(self, message: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(f"[ScraperService] {message}")
        try:
            with open(SCRAPER_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to scraper log: {e}")

    def _embed_product_image(self, image_url: str, text_prompt: str) -> np.ndarray:
        """Download product image and compute Fashion-CLIP vector; fallback to text if fails."""
        if image_url:
            try:
                # Ensure HTTPS
                if image_url.startswith("http://"):
                    image_url = image_url.replace("http://", "https://")
                    
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                }
                res = requests.get(image_url, headers=headers, timeout=6)
                if res.status_code == 200:
                    img = Image.open(BytesIO(res.content))
                    img.load()
                    return self.embedder.embed_image(img)
            except Exception as e:
                self.log_scrape_event(f"Failed to download/embed image {image_url}: {e}")
                
        # Fallback to text embedding
        try:
            return self.embedder.embed_text(text_prompt)
        except Exception as e:
            self.log_scrape_event(f"Failed text embedding fallback for '{text_prompt}': {e}")
            rnd = np.random.randn(EMBEDDING_DIM).astype(np.float32)
            return rnd / np.linalg.norm(rnd)

    def initialize_or_refresh_catalog(self, force_reseed: bool = False) -> Dict[str, Any]:
        """
        Launches clean unique catalog scraping and indexing on startup.
        """
        if self._is_indexing:
            return {
                "status": "indexing",
                "message": "Catalog indexing is already running in the background."
            }

        # Check if valid deduplicated catalog already exists
        if not force_reseed and os.path.exists(PRODUCTS_FILE) and len(self.vector_store.products) >= 50:
            # Verify uniqueness
            ids = [p.get("id") for p in self.vector_store.products]
            if len(ids) == len(set(ids)):
                self.log_scrape_event(f"Loaded existing clean catalog with {len(ids)} unique items.")
                return {
                    "status": "ready",
                    "total_products": len(ids),
                    "index_size": self.vector_store.index.ntotal if self.vector_store.index else 0
                }

        # Start background indexing
        self._is_indexing = True
        self._indexing_thread = threading.Thread(
            target=self._run_clean_catalog_build,
            daemon=True
        )
        self._indexing_thread.start()

        return {
            "status": "started",
            "message": "Background clean multi-retailer catalog scraping & embedding started."
        }

    def _run_clean_catalog_build(self):
        try:
            self.log_scrape_event("Starting clean multi-retailer catalog scraping & indexing...")
            
            categories = ["dresses", "tops", "bottoms", "ethnic", "footwear"]
            all_candidate_products: List[Dict[str, Any]] = []

            # 1. Scrape live Myntra products across all 5 categories
            for cat in categories:
                self.log_scrape_event(f"Scraping live Myntra products for category: '{cat}'...")
                try:
                    myntra_items = self.myntra.scrape_category(cat, limit=35)
                    self.log_scrape_event(f"Retrieved {len(myntra_items)} items from Myntra for '{cat}'.")
                    all_candidate_products.extend(myntra_items)
                except Exception as e:
                    self.log_scrape_event(f"Error scraping Myntra for '{cat}': {e}")
                time.sleep(1.0)

            # 2. Add curated direct products for Ajio & Max Fashion
            curated_items = get_curated_retailer_catalog()
            self.log_scrape_event(f"Loaded {len(curated_items)} curated direct products for Ajio & Max Fashion.")
            all_candidate_products.extend(curated_items)

            # 3. Strict Deduplication across ID, Product URL, and Image URL
            clean_products = []
            seen_ids = set()
            seen_urls = set()
            seen_imgs = set()

            for p in all_candidate_products:
                pid = p.get("id")
                purl = p.get("product_url")
                pimg = p.get("image_url")

                if not pid or pid in seen_ids:
                    continue
                if purl and purl in seen_urls:
                    continue
                if pimg and pimg in seen_imgs:
                    continue

                seen_ids.add(pid)
                if purl:
                    seen_urls.add(purl)
                if pimg:
                    seen_imgs.add(pimg)

                clean_products.append(p)

            self.log_scrape_event(f"Deduplication complete: {len(clean_products)} unique products across 5 categories.")

            # 4. Generate Fashion-CLIP embeddings for all unique products
            self.log_scrape_event("Generating Fashion-CLIP embeddings for unique products...")
            indexed_products = []
            all_embeddings = []

            for idx, p in enumerate(clean_products):
                prompt = f"{p.get('color', '')} {p.get('brand', '')} {p.get('title', '')} {p.get('category', '')}".strip()
                img_url = p.get("image_url", "")
                
                vec = self._embed_product_image(img_url, prompt)
                p["embedding"] = vec.tolist()
                indexed_products.append(p)
                all_embeddings.append(vec)

                if (idx + 1) % 20 == 0 or (idx + 1) == len(clean_products):
                    self.log_scrape_event(f"Embedded [{idx + 1}/{len(clean_products)}] products...")
                    # Progressive FAISS index save
                    embeddings_matrix = np.vstack(all_embeddings).astype(np.float32)
                    self.vector_store.build_index(indexed_products, embeddings_matrix)

            self.log_scrape_event(f"Catalog indexing finished! Total unique items indexed: {len(indexed_products)}")
        except Exception as e:
            self.log_scrape_event(f"Error in clean catalog build: {e}")
        finally:
            self._is_indexing = False

    def run_live_category_scrape(self, category: str, retailer: str = "all") -> Dict[str, Any]:
        """Run an on-demand live scrape for a specific category."""
        self.log_scrape_event(f"Starting on-demand scrape: category='{category}', retailer='{retailer}'")
        found_products = []
        
        if retailer.lower() in ["ajio", "all"]:
            found_products.extend(self.ajio.scrape_category(category, limit=25))
        if retailer.lower() in ["myntra", "all"]:
            found_products.extend(self.myntra.scrape_category(category, limit=25))
        if retailer.lower() in ["max fashion", "all"]:
            found_products.extend(self.max_fashion.scrape_category(category, limit=25))

        self.log_scrape_event(f"Scraped {len(found_products)} live products.")
        return {
            "category": category,
            "retailer": retailer,
            "scraped_count": len(found_products),
            "sample_items": found_products[:5]
        }

