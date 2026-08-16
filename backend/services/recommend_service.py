import os
import json
import numpy as np
from typing import List, Dict, Any, Optional

from backend.config import PRODUCTS_FILE, CATALOG_INDEX_FILE, FEEDBACK_FILE, EMBEDDING_DIM
from backend.models.vector_store import CatalogVectorStore
from backend.services.wardrobe_service import WardrobeService

class RecommendationService:
    def __init__(self, wardrobe_service: WardrobeService):
        self.wardrobe_service = wardrobe_service
        self.vector_store = CatalogVectorStore(
            index_path=str(CATALOG_INDEX_FILE),
            products_path=str(PRODUCTS_FILE),
            dim=EMBEDDING_DIM
        )
        self.feedback: Dict[str, Any] = {"likes": {}, "dislikes": {}}
        self.load_feedback()

    def load_feedback(self):
        if os.path.exists(FEEDBACK_FILE):
            try:
                with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                    self.feedback = json.load(f)
            except Exception as e:
                print(f"Error loading feedback: {e}")
                self.feedback = {"likes": {}, "dislikes": {}}
        else:
            self.feedback = {"likes": {}, "dislikes": {}}

    def save_feedback(self):
        os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
        tmp_file = f"{FEEDBACK_FILE}.{os.getpid()}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self.feedback, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, FEEDBACK_FILE)

    def record_feedback(self, product_id: str, is_like: bool, product_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Record thumbs up (+1) or thumbs down (-1) feedback to train the preference vector.
        """
        # Find product embedding if available
        product = None
        for p in self.vector_store.products:
            if p.get("id") == product_id:
                product = p
                break

        embedding = None
        if product and "embedding" in product:
            embedding = product["embedding"]

        feedback_entry = {
            "product_id": product_id,
            "title": product.get("title") if product else product_data.get("title", ""),
            "brand": product.get("brand") if product else product_data.get("brand", ""),
            "category": product.get("category") if product else product_data.get("category", ""),
            "price": product.get("price") if product else product_data.get("price", 0),
            "retailer": product.get("retailer") if product else product_data.get("retailer", ""),
            "embedding": embedding
        }

        if is_like:
            # If previously disliked, remove from dislikes
            self.feedback["dislikes"].pop(product_id, None)
            self.feedback["likes"][product_id] = feedback_entry
        else:
            self.feedback["likes"].pop(product_id, None)
            self.feedback["dislikes"][product_id] = feedback_entry

        self.save_feedback()
        return {
            "status": "success",
            "product_id": product_id,
            "action": "liked" if is_like else "disliked",
            "total_likes": len(self.feedback["likes"]),
            "total_dislikes": len(self.feedback["dislikes"])
        }

    def get_feedback_vectors(self) -> (List[np.ndarray], List[np.ndarray]):
        """Extract liked and disliked embedding vectors to construct taste projection."""
        liked_vecs = []
        for entry in self.feedback.get("likes", {}).values():
            if entry.get("embedding"):
                liked_vecs.append(np.array(entry["embedding"], dtype=np.float32))

        disliked_vecs = []
        for entry in self.feedback.get("dislikes", {}).values():
            if entry.get("embedding"):
                disliked_vecs.append(np.array(entry["embedding"], dtype=np.float32))

        return liked_vecs, disliked_vecs

    def recommend(
        self,
        garment_id: Optional[str] = None,
        category: Optional[str] = None,
        retailer: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        size: Optional[str] = None,
        sort_by: str = "relevance",
        preference_weight: float = 0.25,
        top_k: int = 40
    ) -> Dict[str, Any]:
        """
        Query recommendations matching either a specific wardrobe garment ID or the full style profile.
        """
        query_vector = None
        source_garment = None

        if garment_id and garment_id != "all":
            source_garment = self.wardrobe_service.get_item_by_id(garment_id)
            if source_garment and "embedding" in source_garment:
                query_vector = np.array(source_garment["embedding"], dtype=np.float32)
                # If category filter is not set, default to the garment's detected category for relevance
                if not category or category.lower() == "all":
                    category = source_garment.get("category", "all")
        
        if query_vector is None:
            # Fallback to general style profile
            query_vector = self.wardrobe_service.get_style_profile_vector()

        if query_vector is None:
            # If no wardrobe items scanned yet, use zero vector or first product vector
            query_vector = np.ones(EMBEDDING_DIM, dtype=np.float32) / np.sqrt(EMBEDDING_DIM)

        liked_vecs, disliked_vecs = self.get_feedback_vectors()

        raw_results = self.vector_store.search(
            query_vector=query_vector,
            category=category,
            retailer=retailer,
            min_price=min_price,
            max_price=max_price,
            size=size,
            sort_by=sort_by,
            liked_vectors=liked_vecs,
            disliked_vectors=disliked_vecs,
            preference_weight=preference_weight,
            top_k=top_k
        )

        # Annotate each product with user's existing like/dislike status
        annotated_results = []
        for item in raw_results:
            pid = item.get("id")
            item_copy = item.copy()
            item_copy["user_feedback"] = "liked" if pid in self.feedback["likes"] else ("disliked" if pid in self.feedback["dislikes"] else None)
            annotated_results.append(item_copy)

        return {
            "total_matches": len(annotated_results),
            "source_garment": {k: v for k, v in source_garment.items() if k != "embedding"} if source_garment else None,
            "applied_filters": {
                "garment_id": garment_id,
                "category": category,
                "retailer": retailer,
                "min_price": min_price,
                "max_price": max_price,
                "size": size,
                "sort_by": sort_by,
                "preference_weight": preference_weight
            },
            "user_taste_stats": {
                "liked_count": len(self.feedback["likes"]),
                "disliked_count": len(self.feedback["dislikes"]),
                "personalization_active": len(liked_vecs) > 0 or len(disliked_vecs) > 0
            },
            "products": annotated_results
        }

    def get_style_insights(self) -> Dict[str, Any]:
        """
        Analyze user's wardrobe and liked products to extract aesthetic themes,
        dominant color frequencies, category distribution, and retail preference.
        """
        wardrobe_items = self.wardrobe_service.wardrobe_data.get("items", [])
        categories: Dict[str, int] = {}
        all_colors: List[str] = []

        for item in wardrobe_items:
            cat = item.get("category", "other").capitalize()
            categories[cat] = categories.get(cat, 0) + 1
            all_colors.extend(item.get("colors", []))

        # Liked products analysis
        liked_brands: Dict[str, int] = {}
        liked_retailers: Dict[str, int] = {}
        for entry in self.feedback.get("likes", {}).values():
            b = entry.get("brand", "Unknown")
            r = entry.get("retailer", "Unknown")
            liked_brands[b] = liked_brands.get(b, 0) + 1
            liked_retailers[r] = liked_retailers.get(r, 0) + 1

        return {
            "total_wardrobe_pieces": len(wardrobe_items),
            "category_distribution": categories,
            "signature_colors": list(dict.fromkeys(all_colors))[:8],
            "favorite_brands": dict(sorted(liked_brands.items(), key=lambda x: x[1], reverse=True)[:5]),
            "preferred_retailers": dict(sorted(liked_retailers.items(), key=lambda x: x[1], reverse=True)[:3]),
            "liked_count": len(self.feedback["likes"]),
            "disliked_count": len(self.feedback["dislikes"])
        }
