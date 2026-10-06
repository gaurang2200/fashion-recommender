import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
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
        query_vector: Optional[np.ndarray] = None,
        query_vectors: Optional[List[np.ndarray]] = None,
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
        Search catalog with multi-cluster vector similarity, K-NN preference reranking, and metadata filters.
        """
        if self.index is None or self.index.ntotal == 0 or len(self.products) == 0:
            return []

        # Collect and normalize all query vectors (from single vector or cluster list)
        q_list = []
        if query_vectors and len(query_vectors) > 0:
            q_list = query_vectors
        elif query_vector is not None:
            q_list = [query_vector]

        if not q_list:
            return []

        norm_q_list = []
        for q in q_list:
            q_arr = np.array(q, dtype=np.float32).reshape(1, -1)
            q_norm = np.linalg.norm(q_arr)
            if q_norm > 0:
                q_arr = q_arr / q_norm
            norm_q_list.append(q_arr[0])

        q_matrix = np.array(norm_q_list, dtype=np.float32)

        # Search FAISS across all cluster centroids simultaneously
        k_search = min(self.index.ntotal, 500)
        scores, indices = self.index.search(q_matrix, k_search)

        # Aggregate maximum cluster similarity for each candidate product index
        best_sim_map: Dict[int, float] = {}
        for k_idx in range(len(q_matrix)):
            for sim_score, prod_idx in zip(scores[k_idx], indices[k_idx]):
                if prod_idx < 0 or prod_idx >= len(self.products):
                    continue
                prod_idx = int(prod_idx)
                sim_val = float(sim_score)
                if prod_idx not in best_sim_map or sim_val > best_sim_map[prod_idx]:
                    best_sim_map[prod_idx] = sim_val

        # Prepare liked/disliked matrix for K-NN feedback reranking
        likes_matrix = None
        if liked_vectors and len(liked_vectors) > 0:
            l_list = []
            for lv in liked_vectors:
                l_arr = np.array(lv, dtype=np.float32)
                l_norm = np.linalg.norm(l_arr)
                if l_norm > 0:
                    l_arr = l_arr / l_norm
                l_list.append(l_arr)
            likes_matrix = np.array(l_list, dtype=np.float32)

        dislikes_matrix = None
        if disliked_vectors and len(disliked_vectors) > 0:
            d_list = []
            for dv in disliked_vectors:
                d_arr = np.array(dv, dtype=np.float32)
                d_norm = np.linalg.norm(d_arr)
                if d_norm > 0:
                    d_arr = d_arr / d_norm
                d_list.append(d_arr)
            dislikes_matrix = np.array(d_list, dtype=np.float32)

        results = []
        seen_res_ids = set()
        seen_res_urls = set()

        for idx, raw_sim in best_sim_map.items():
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

            # --- K-NN Preference Reranking ---
            pref_boost = 0.0
            prod_vec = None
            if "embedding" in product:
                prod_vec = np.array(product["embedding"], dtype=np.float32)
                p_norm = np.linalg.norm(prod_vec)
                if p_norm > 0:
                    prod_vec = prod_vec / p_norm

            if prod_vec is not None and (likes_matrix is not None or dislikes_matrix is not None):
                like_boost = 0.0
                if likes_matrix is not None:
                    like_sims = np.dot(likes_matrix, prod_vec)
                    like_boost = float(np.max(like_sims))

                dislike_penalty = 0.0
                if dislikes_matrix is not None:
                    dislike_sims = np.dot(dislikes_matrix, prod_vec)
                    dislike_penalty = float(np.max(dislike_sims))

                pref_boost = like_boost - 0.6 * dislike_penalty
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

