import os
import time
import json
import datetime
import threading
import requests
from io import BytesIO
from PIL import Image
from typing import List, Dict, Any, Optional
import numpy as np

from backend.config import PRODUCTS_FILE, SCRAPER_LOG_FILE, EMBEDDING_DIM
from backend.models.embedder import FashionEmbedder
from backend.models.vector_store import CatalogVectorStore
from backend.scrapers.seed_catalog import get_curated_retailer_catalog
from backend.scrapers.ajio import AjioScraper
from backend.scrapers.myntra import MyntraScraper
from backend.scrapers.max_fashion import MaxFashionScraper

class ScraperService:
    def __init__(self, embedder: FashionEmbedder, vector_store: CatalogVectorStore, recommend_service: Any = None):
        self.embedder = embedder
        self.vector_store = vector_store
        self.recommend_service = recommend_service
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

    def _clean_query_string(self, text: str) -> str:
        """Strip hex color codes, raw filenames, numbers, and query noise."""
        import re
        text = re.sub(r'#[0-9a-fA-F]{6}', '', text)
        text = re.sub(r'\b(dress|top|pant|skirt|kurta|shoe|piece)\d+\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\.[a-zA-Z]{3,4}', '', text)
        words = [w for w in text.split() if len(w) > 2 and w.lower() not in ["women", "men", "buy", "online", "with", "for"]]
        return " ".join(words)

    def _extract_detailed_prompts(self, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Step 1: Extract detailed descriptions from liked clothes and wardrobe items to drive scraping.
        """
        prompts = []
        target_cat = (category_filter or "all").lower()

        # 1. Pull liked items from recommend_service.feedback["likes"]
        liked_entries = []
        if self.recommend_service and hasattr(self.recommend_service, "feedback"):
            liked_entries = list(self.recommend_service.feedback.get("likes", {}).values())

        for entry in liked_entries:
            cat = (entry.get("category") or "tops").lower()
            effective_cat = cat
            if target_cat != "all" and cat != target_cat:
                effective_cat = target_cat
                
            brand = entry.get("brand", "")
            title = entry.get("title", "")
            clean_title = self._clean_query_string(title)
            
            query = f"{brand} {clean_title} {effective_cat}".strip()
            if query and len(query.split()) >= 2 and query not in [p["query"] for p in prompts]:
                prompts.append({
                    "query": query,
                    "category": effective_cat,
                    "source": "liked",
                    "title": title
                })

        # 2. Pull wardrobe garments
        wardrobe_items = []
        if self.recommend_service and hasattr(self.recommend_service, "wardrobe_service"):
            wardrobe_items = self.recommend_service.wardrobe_service.wardrobe_data.get("items", [])

        for item in wardrobe_items:
            cat = (item.get("category") or "tops").lower()
            effective_cat = cat
            if target_cat != "all" and cat != target_cat:
                effective_cat = target_cat

            source_name = self._clean_query_string(item.get("source_image", ""))
            query = f"{source_name} {effective_cat}".strip()
            if query and len(query.split()) >= 2 and query not in [p["query"] for p in prompts]:
                prompts.append({
                    "query": query,
                    "category": effective_cat,
                    "source": "wardrobe"
                })

        # Fallbacks if no specific prompts generated
        if not prompts:
            cat = target_cat if target_cat != "all" else "dresses"
            prompts.append({"query": f"floral printed {cat}", "category": cat, "source": "default"})
            prompts.append({"query": f"cotton casual {cat}", "category": cat, "source": "default"})

        return prompts


    def _segment_and_embed_scraped_image(self, image_url: str, text_prompt: str) -> np.ndarray:
        """
        Step 2: Downloads candidate product image, isolates ONLY the cloth (background removal/segmentation),
        and computes Fashion-CLIP embedding on the clean garment crop.
        """
        if image_url:
            try:
                if image_url.startswith("http://"):
                    image_url = image_url.replace("http://", "https://")
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                }
                res = requests.get(image_url, headers=headers, timeout=6)
                if res.status_code == 200:
                    img = Image.open(BytesIO(res.content))
                    img.load()
                    
                    # Segment & isolate only the cloth if segmenter is available
                    if self.recommend_service and hasattr(self.recommend_service, "wardrobe_service"):
                        segmenter = self.recommend_service.wardrobe_service.segmenter
                        img_rgba = img.convert("RGBA")
                        
                        # Background removal to isolate cloth
                        from rembg import remove
                        segmented_img = remove(img_rgba, session=segmenter.session)
                        
                        alpha = np.array(segmented_img)[:, :, 3]
                        pos_pixels = np.where(alpha > 20)
                        if len(pos_pixels[0]) > 0:
                            ymin, ymax = np.min(pos_pixels[0]), np.max(pos_pixels[0])
                            xmin, xmax = np.min(pos_pixels[1]), np.max(pos_pixels[1])
                            cropped_cloth = segmented_img.crop((xmin, ymin, xmax, ymax))
                        else:
                            cropped_cloth = segmented_img

                        crop_w, crop_h = cropped_cloth.size
                        square_size = max(crop_w, crop_h) + 20
                        canvas = Image.new("RGBA", (square_size, square_size), (255, 255, 255, 255))
                        offset = ((square_size - crop_w) // 2, (square_size - crop_h) // 2)
                        canvas.paste(cropped_cloth, offset, cropped_cloth)

                        return self.embedder.embed_image(canvas.convert("RGB"))
                    else:
                        return self.embedder.embed_image(img)
            except Exception as e:
                self.log_scrape_event(f"Notice during cloth segmentation for {image_url}: {e}")

        # Fallback to text prompt embedding
        try:
            return self.embedder.embed_text(text_prompt)
        except Exception as e:
            rnd = np.random.randn(EMBEDDING_DIM).astype(np.float32)
            return rnd / np.linalg.norm(rnd)

    def _get_target_taste_vector(self) -> np.ndarray:
        """Construct composite target taste vector from liked dresses + wardrobe items."""
        liked_vecs = []
        if self.recommend_service:
            liked_vecs, _ = self.recommend_service.get_feedback_vectors()
            
        wardrobe_vec = None
        if self.recommend_service and hasattr(self.recommend_service, "wardrobe_service"):
            wardrobe_vec = self.recommend_service.wardrobe_service.get_style_profile_vector()

        acc = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        count = 0
        if liked_vecs:
            acc += np.mean(liked_vecs, axis=0)
            count += 1
        if wardrobe_vec is not None:
            acc += wardrobe_vec
            count += 1

        if count > 0:
            norm = np.linalg.norm(acc)
            if norm > 0:
                return (acc / norm).astype(np.float32)

        rnd = np.ones(EMBEDDING_DIM, dtype=np.float32)
        return rnd / np.linalg.norm(rnd)

    def _filter_and_index_scraped_items(self, candidate_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 3: Embeds candidate clothes after isolating garment, calculates similarity against taste profile,
        and returns only the top 40% most similar matches.
        """
        if not candidate_products:
            return []

        target_taste_vec = self._get_target_taste_vector()
        self.log_scrape_event(f"Step 2 & 3: Isolating cloth & computing Fashion-CLIP similarity for {len(candidate_products)} scraped candidates...")

        scored_candidates = []
        for idx, p in enumerate(candidate_products):
            prompt = f"{p.get('color', '')} {p.get('brand', '')} {p.get('title', '')} {p.get('category', '')}".strip()
            img_url = p.get("image_url", "")
            
            vec = self._segment_and_embed_scraped_image(img_url, prompt)
            p["embedding"] = vec.tolist()
            
            sim_score = float(np.dot(target_taste_vec, vec))
            p["similarity_score"] = round(sim_score, 4)
            scored_candidates.append((sim_score, p))

            if (idx + 1) % 10 == 0 or (idx + 1) == len(candidate_products):
                self.log_scrape_event(f"Segmented & embedded cloth for [{idx + 1}/{len(candidate_products)}] candidates...")

        # Rank candidates by similarity score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Filter to keep top 40% most similar items
        keep_count = max(4, int(np.ceil(len(scored_candidates) * 0.40)))
        top_matches = [p for _, p in scored_candidates[:keep_count]]

        self.log_scrape_event(f"Similarity filter complete: Retained top {len(top_matches)} of {len(candidate_products)} candidates (Top 40% highest similarity matches).")
        return top_matches

    def _embed_product_image(self, image_url: str, text_prompt: str) -> np.ndarray:
        return self._segment_and_embed_scraped_image(image_url, text_prompt)


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
        """
        Step 1, 2 & 3: Runs targeted scraping driven by liked + wardrobe detailed descriptions,
        purges disliked items, isolates the cloth (removes background/clutter), computes Fashion-CLIP embeddings,
        marks newly scraped items as is_new=True, and indexes the top 40% most similar matches.
        """
        self.log_scrape_event(f"Starting targeted scrape driven by liked & wardrobe items: category='{category}', retailer='{retailer}'")
        
        # Purge disliked items from active catalog upon Scrape Now
        disliked_ids = set()
        if self.recommend_service and hasattr(self.recommend_service, "feedback"):
            disliked_ids = set(self.recommend_service.feedback.get("dislikes", {}).keys())

        if disliked_ids:
            initial_count = len(self.vector_store.products)
            clean_catalog = [p for p in self.vector_store.products if p.get("id") not in disliked_ids]
            purged_count = initial_count - len(clean_catalog)
            if purged_count > 0:
                self.vector_store.products = clean_catalog
                embeddings_list = [np.array(p["embedding"], dtype=np.float32) for p in clean_catalog if "embedding" in p]
                if embeddings_list:
                    embeddings_matrix = np.vstack(embeddings_list).astype(np.float32)
                    self.vector_store.build_index(clean_catalog, embeddings_matrix)
                self.log_scrape_event(f"Purged {purged_count} disliked products from catalog and updated FAISS index.")

        # Step 1: Extract detailed search descriptions from liked items & wardrobe
        detailed_prompts = self._extract_detailed_prompts(category)
        self.log_scrape_event(f"Step 1: Generated {len(detailed_prompts)} detailed search prompts from liked & wardrobe garments.")

        found_products = []
        for p_info in detailed_prompts[:5]: # Scrape for top 5 detailed prompts
            query = p_info["query"]
            cat = p_info["category"]
            self.log_scrape_event(f"Scraping platforms for detailed prompt: '{query}' (category: {cat})...")

            if retailer.lower() in ["myntra", "all"]:
                try:
                    m_items = self.myntra.scrape_search(query, category=cat, limit=20)
                    found_products.extend(m_items)
                except Exception as e:
                    self.log_scrape_event(f"Myntra search error for '{query}': {e}")

            if retailer.lower() in ["ajio", "all"]:
                try:
                    a_items = self.ajio.scrape_category(cat, limit=15)
                    found_products.extend(a_items)
                except Exception as e:
                    self.log_scrape_event(f"Ajio scrape error for '{cat}': {e}")

            if retailer.lower() in ["max fashion", "all"]:
                try:
                    mf_items = self.max_fashion.scrape_category(cat, limit=15)
                    found_products.extend(mf_items)
                except Exception as e:
                    self.log_scrape_event(f"Max Fashion scrape error for '{cat}': {e}")

            time.sleep(0.5)

        self.log_scrape_event(f"Scraped {len(found_products)} candidate live products across platforms.")

        # Strict Deduplication against current catalog
        current_products = list(self.vector_store.products)
        seen_ids = set(p.get("id") for p in current_products if p.get("id"))
        seen_urls = set(p.get("product_url") for p in current_products if p.get("product_url"))
        seen_imgs = set(p.get("image_url") for p in current_products if p.get("image_url"))

        new_items_to_process = []
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

            new_items_to_process.append(p)

        self.log_scrape_event(f"Identified {len(new_items_to_process)} completely new unique candidate products.")

        if not new_items_to_process:
            return {
                "category": category,
                "retailer": retailer,
                "scraped_count": len(found_products),
                "new_indexed_count": 0,
                "total_catalog_size": len(self.vector_store.products),
                "sample_items": []
            }

        # Step 2 & 3: Isolate cloth (segmentation), compute CLIP embeddings, and filter top 40% similarity matches
        filtered_top_products = self._filter_and_index_scraped_items(new_items_to_process)

        if filtered_top_products:
            # Reset is_new flag on existing catalog items
            for p in current_products:
                p["is_new"] = False

            all_current_embeddings = []
            for p in current_products:
                if "embedding" in p:
                    all_current_embeddings.append(np.array(p["embedding"], dtype=np.float32))
                else:
                    rnd = np.random.randn(EMBEDDING_DIM).astype(np.float32)
                    rnd = rnd / np.linalg.norm(rnd)
                    p["embedding"] = rnd.tolist()
                    all_current_embeddings.append(rnd)

            for p in filtered_top_products:
                p["is_new"] = True
                current_products.append(p)
                all_current_embeddings.append(np.array(p["embedding"], dtype=np.float32))

            # Atomic rebuild of FAISS index
            embeddings_matrix = np.vstack(all_current_embeddings).astype(np.float32)
            self.vector_store.build_index(current_products, embeddings_matrix)
            self.log_scrape_event(f"Successfully added & indexed top {len(filtered_top_products)} cloth-segmented products (marked as NEW). Total catalog size: {len(current_products)}")

        return {
            "category": category,
            "retailer": retailer,
            "scraped_count": len(found_products),
            "new_indexed_count": len(filtered_top_products),
            "total_catalog_size": len(self.vector_store.products),
            "sample_items": filtered_top_products[:5]
        }


