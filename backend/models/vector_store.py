import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

class CatalogVectorStore:
    """
    FAISS-backed vector database for catalog products with multi-attribute filtering
    and personalized preference reranking based on user likes/dislikes.
    """
    def __init__(self, index_path: str, products_path: str, dim: int = 512):
        self.index_path = index_path
        self.products_path = products_path
        self.dim = dim
        self.index = None
        self.products: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        """Load FAISS index and product metadata."""
        if os.path.exists(self.products_path):
            with open(self.products_path, "r", encoding="utf-8") as f:
                self.products = json.load(f)
        else:
            self.products = []

        if os.path.exists(self.index_path) and len(self.products) > 0:
            self.index = faiss.read_index(self.index_path)
        else:
            # IndexFlatIP calculates inner products, equivalent to cosine similarity for normalized vectors
            self.index = faiss.IndexFlatIP(self.dim)

    def save(self):
        """Save FAISS index and products list with atomic file replacement."""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.products_path), exist_ok=True)
        pid = os.getpid()
        if self.index is not None:
            tmp_index = f"{self.index_path}.{pid}.tmp"
            faiss.write_index(self.index, tmp_index)
            os.replace(tmp_index, self.index_path)
            
        tmp_products = f"{self.products_path}.{pid}.tmp"
        with open(tmp_products, "w", encoding="utf-8") as f:
            json.dump(self.products, f, indent=2, ensure_ascii=False)
        os.replace(tmp_products, self.products_path)

    def build_index(self, products: List[Dict[str, Any]], embeddings: np.ndarray):
        """Rebuild FAISS index from an array of embeddings."""
        assert len(products) == len(embeddings), "Products and embeddings count mismatch"
        self.products = products
        self.index = faiss.IndexFlatIP(self.dim)
        if len(embeddings) > 0:
            # Ensure float32 and normalized
            embeddings = embeddings.astype(np.float32)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            embeddings = embeddings / norms
            self.index.add(embeddings)
        self.save()

    def search(
        self,
        query_vector: np.ndarray,
        category: Optional[str] = None,
        retailer: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        size: Optional[str] = None,
        sort_by: str = "relevance", # "relevance", "price_asc", "price_desc", "discount"
        liked_vectors: Optional[List[np.ndarray]] = None,
        disliked_vectors: Optional[List[np.ndarray]] = None,
        preference_weight: float = 0.25,
        top_k: int = 40
    ) -> List[Dict[str, Any]]:
        """
        Search catalog with vector similarity, active preference boost, and metadata filters.
        """
        if self.index is None or self.index.ntotal == 0 or len(self.products) == 0:
            return []

        # Ensure query is 2D float32 normalized
        q_vec = query_vector.reshape(1, -1).astype(np.float32)
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        # Compute raw similarity scores across all products
        # FAISS search on top ntotal items
        k_search = min(self.index.ntotal, 500)
        scores, indices = self.index.search(q_vec, k_search)
        
        scores = scores[0]
        indices = indices[0]

        # Calculate user taste displacement vector from likes/dislikes
        pref_vec = None
        if liked_vectors or disliked_vectors:
            likes = np.array(liked_vectors) if liked_vectors and len(liked_vectors) > 0 else None
            dislikes = np.array(disliked_vectors) if disliked_vectors and len(disliked_vectors) > 0 else None
            
            p_acc = np.zeros(self.dim, dtype=np.float32)
            if likes is not None and len(likes) > 0:
                p_acc += np.mean(likes, axis=0)
            if dislikes is not None and len(dislikes) > 0:
                p_acc -= 0.6 * np.mean(dislikes, axis=0)
                
            p_norm = np.linalg.norm(p_acc)
            if p_norm > 0:
                pref_vec = (p_acc / p_norm).astype(np.float32)

        results = []
        seen_res_ids = set()
        seen_res_urls = set()
        for sim_score, idx in zip(scores, indices):
            if idx < 0 or idx >= len(self.products):
                continue
            product = self.products[idx].copy()
            pid = product.get("id")
            purl = product.get("product_url")
            if pid in seen_res_ids or (purl and purl in seen_res_urls):
                continue
            
            # --- Metadata Filtering ---
            if category and category.lower() != "all":
                if category.lower() == "new_arrivals":
                    if not product.get("is_new"):
                        continue
                else:
                    prod_cat = product.get("category", "").lower()
                    if category.lower() not in prod_cat and prod_cat not in category.lower():
                        continue

            if retailer and retailer.lower() != "all":
                if product.get("retailer", "").lower() != retailer.lower():
                    continue

            price = float(product.get("price", 0))
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue

            if size and size.lower() != "all":
                available_sizes = [s.upper() for s in product.get("sizes", [])]
                if size.upper() not in available_sizes and "FREE SIZE" not in available_sizes:
                    continue

            # --- Preference Reranking ---
            raw_sim = float(sim_score)
            pref_boost = 0.0
            
            if pref_vec is not None and "embedding" in product:
                prod_vec = np.array(product["embedding"], dtype=np.float32)
                p_norm = np.linalg.norm(prod_vec)
                if p_norm > 0:
                    prod_vec = prod_vec / p_norm
                pref_boost = float(np.dot(pref_vec, prod_vec))
                final_score = (1.0 - preference_weight) * raw_sim + preference_weight * pref_boost
            else:
                final_score = raw_sim

            # Clamp scores between 0 and 1 for clean UI display
            similarity_pct = max(0.0, min(100.0, ((raw_sim + 1.0) / 2.0) * 100.0))
            match_pct = max(0.0, min(100.0, ((final_score + 1.0) / 2.0) * 100.0))

            product["similarity_score"] = round(raw_sim, 4)
            product["preference_boost"] = round(pref_boost, 4)
            product["final_score"] = round(final_score, 4)
            product["match_percentage"] = round(match_pct, 1)
            product["raw_similarity_pct"] = round(similarity_pct, 1)
            product["index_id"] = int(idx)
            
            # Don't send bulky embedding vector in response
            if "embedding" in product:
                del product["embedding"]

            seen_res_ids.add(pid)
            if purl:
                seen_res_urls.add(purl)
            results.append(product)

        # --- Sorting ---
        if sort_by == "relevance":
            results.sort(key=lambda x: x["final_score"], reverse=True)
        elif sort_by == "price_asc":
            results.sort(key=lambda x: x.get("price", 0))
        elif sort_by == "price_desc":
            results.sort(key=lambda x: x.get("price", 0), reverse=True)
        elif sort_by == "discount":
            results.sort(key=lambda x: x.get("discount_pct", 0), reverse=True)

        # Ensure strict uniqueness in returned results
        unique_results = []
        seen_final_ids = set()
        seen_final_urls = set()
        for item in results:
            iid = item.get("id")
            iurl = item.get("product_url")
            if iid not in seen_final_ids and (not iurl or iurl not in seen_final_urls):
                seen_final_ids.add(iid)
                if iurl:
                    seen_final_urls.add(iurl)
                unique_results.append(item)

        return unique_results[:top_k]

