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

    def scrape_and_index_for_new_garments(self, new_items: List[Dict[str, Any]], limit_per_item: int = 30) -> Dict[str, Any]:
        """
        Background scraper triggered when new garments are scanned in the wardrobe.
        Extracts categories & colors, scrapes live matching products from Myntra,
        downloads images, computes Fashion-CLIP embeddings, and enriches the FAISS index.
        """
        if not new_items:
            return {"status": "skipped", "message": "No new items provided."}

        if self._is_indexing:
            self.log_scrape_event("Another indexing process is already running. Scheduling discovery for new garments...")

        # Start thread
        thread = threading.Thread(
            target=self._run_scrape_and_index_for_new_garments,
            args=(new_items, limit_per_item),
            daemon=True
        )
        self._is_indexing = True
        thread.start()

        return {
            "status": "started",
            "message": f"Started live product discovery for {len(new_items)} new garments."
        }

    def _run_scrape_and_index_for_new_garments(self, new_items: List[Dict[str, Any]], limit_per_item: int = 30):
        try:
            self.log_scrape_event(f"Starting targeted live product discovery for {len(new_items)} newly scanned garments...")
            
            # Load current products
            current_products = list(self.vector_store.products)
            seen_ids = set(p.get("id") for p in current_products if p.get("id"))
            seen_urls = set(p.get("product_url") for p in current_products if p.get("product_url"))
            seen_imgs = set(p.get("image_url") for p in current_products if p.get("image_url"))

            newly_discovered_products = []

            for idx, item in enumerate(new_items):
                cat = item.get("category", "tops").lower()
                colors = item.get("colors", [])
                
                # Formulate query
                color_desc = " ".join(colors[:2]) if colors else ""
                search_query = f"{color_desc} {cat}".strip()
                
                self.log_scrape_event(f"[{idx+1}/{len(new_items)}] Scraping live Myntra items matching '{search_query}' (Category: {cat})...")
                
                scraped = self.myntra.scrape_search(search_query, category=cat, limit=limit_per_item)
                # Fallback to category scraping if specific query returned 0 items
                if not scraped:
                    scraped = self.myntra.scrape_category(cat, limit=limit_per_item)

                self.log_scrape_event(f"Retrieved {len(scraped)} candidate items for '{search_query}'.")

                for p in scraped:
                    pid = p.get("id")
                    purl = p.get("product_url")
                    pimg = p.get("image_url")

                    if not pid or pid in seen_ids or (purl and purl in seen_urls) or (pimg and pimg in seen_imgs):
                        continue

                    seen_ids.add(pid)
                    if purl:
                        seen_urls.add(purl)
                    if pimg:
                        seen_imgs.add(pimg)

                    newly_discovered_products.append(p)

                time.sleep(1.0)

            self.log_scrape_event(f"Found {len(newly_discovered_products)} completely unique new products to index.")

            if newly_discovered_products:
                self.log_scrape_event("Downloading images and computing Fashion-CLIP embeddings for new products...")
                
                all_current_embeddings = []
                for p in current_products:
                    if "embedding" in p:
                        all_current_embeddings.append(np.array(p["embedding"], dtype=np.float32))
                    else:
                        rnd = np.random.randn(EMBEDDING_DIM).astype(np.float32)
                        rnd = rnd / np.linalg.norm(rnd)
                        p["embedding"] = rnd.tolist()
                        all_current_embeddings.append(rnd)

                for idx, p in enumerate(newly_discovered_products):
                    prompt = f"{p.get('color', '')} {p.get('brand', '')} {p.get('title', '')} {p.get('category', '')}".strip()
                    img_url = p.get("image_url", "")
                    
                    vec = self._embed_product_image(img_url, prompt)
                    p["embedding"] = vec.tolist()
                    current_products.append(p)
                    all_current_embeddings.append(vec)

                    if (idx + 1) % 10 == 0 or (idx + 1) == len(newly_discovered_products):
                        self.log_scrape_event(f"Embedded [{idx + 1}/{len(newly_discovered_products)}] new items...")
                        embeddings_matrix = np.vstack(all_current_embeddings).astype(np.float32)
                        self.vector_store.build_index(current_products, embeddings_matrix)

                self.log_scrape_event(f"New garment live enrichment complete! Total catalog items: {len(current_products)}")
            else:
                self.log_scrape_event("No new unique products found to add.")
        except Exception as e:
            self.log_scrape_event(f"Error during new garment scraping: {e}")
        finally:
            self._is_indexing = False

    def is_indexing(self) -> bool:
        return self._is_indexing

    def run_live_category_scrape(self, category: str, retailer: str = "all") -> Dict[str, Any]:
        """Run an on-demand live scrape for a specific category, compute CLIP embeddings, and index new items."""
        self.log_scrape_event(f"Starting on-demand scrape: category='{category}', retailer='{retailer}'")
        found_products = []
        
        if retailer.lower() in ["ajio", "all"]:
            try:
                found_products.extend(self.ajio.scrape_category(category, limit=25))
            except Exception as e:
                self.log_scrape_event(f"Ajio scrape error: {e}")
        if retailer.lower() in ["myntra", "all"]:
            try:
                found_products.extend(self.myntra.scrape_category(category, limit=30))
            except Exception as e:
                self.log_scrape_event(f"Myntra scrape error: {e}")
        if retailer.lower() in ["max fashion", "all"]:
            try:
                found_products.extend(self.max_fashion.scrape_category(category, limit=25))
            except Exception as e:
                self.log_scrape_event(f"Max Fashion scrape error: {e}")

        self.log_scrape_event(f"Scraped {len(found_products)} candidate live products from retailers.")

        # Strict Deduplication against current catalog
        current_products = list(self.vector_store.products)
        seen_ids = set(p.get("id") for p in current_products if p.get("id"))
        seen_urls = set(p.get("product_url") for p in current_products if p.get("product_url"))
        seen_imgs = set(p.get("image_url") for p in current_products if p.get("image_url"))

        new_items_to_add = []
        for p in found_products:
            pid = p.get("id")
            purl = p.get("product_url")
            pimg = p.get("image_url")

            if not pid or pid in seen_ids or (purl and purl in seen_urls) or (pimg and pimg in seen_imgs):
                continue

            seen_ids.add(pid)
            if purl:
                seen_urls.add(purl)
            if pimg:
                seen_imgs.add(pimg)

            new_items_to_add.append(p)

        self.log_scrape_event(f"Identified {len(new_items_to_add)} completely new unique products to index.")

        if new_items_to_add:
            self.log_scrape_event("Downloading images and computing Fashion-CLIP embeddings for new products...")
            all_current_embeddings = []
            for p in current_products:
                if "embedding" in p:
                    all_current_embeddings.append(np.array(p["embedding"], dtype=np.float32))
                else:
                    rnd = np.random.randn(EMBEDDING_DIM).astype(np.float32)
                    rnd = rnd / np.linalg.norm(rnd)
                    p["embedding"] = rnd.tolist()
                    all_current_embeddings.append(rnd)

            for idx, p in enumerate(new_items_to_add):
                prompt = f"{p.get('color', '')} {p.get('brand', '')} {p.get('title', '')} {p.get('category', '')}".strip()
                img_url = p.get("image_url", "")
                
                vec = self._embed_product_image(img_url, prompt)
                p["embedding"] = vec.tolist()
                current_products.append(p)
                all_current_embeddings.append(vec)

            # Build and save FAISS index
            embeddings_matrix = np.vstack(all_current_embeddings).astype(np.float32)
            self.vector_store.build_index(current_products, embeddings_matrix)
            self.log_scrape_event(f"Successfully added and indexed {len(new_items_to_add)} new products. Total catalog size: {len(current_products)}")

        return {
            "category": category,
            "retailer": retailer,
            "scraped_count": len(found_products),
            "new_indexed_count": len(new_items_to_add),
            "total_catalog_size": len(self.vector_store.products),
            "sample_items": new_items_to_add[:5] if new_items_to_add else found_products[:5]
        }

