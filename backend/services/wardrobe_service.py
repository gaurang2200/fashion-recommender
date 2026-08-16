import os
import glob
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from backend.config import CLOTHES_DIR, CROPS_DIR, WARDROBE_FILE, EMBEDDING_MODEL_NAME, DEVICE
from backend.models.segmenter import GarmentSegmenter
from backend.models.embedder import FashionEmbedder

class WardrobeService:
    def __init__(self):
        self.segmenter = GarmentSegmenter()
        self.embedder = FashionEmbedder(model_name=EMBEDDING_MODEL_NAME, device=DEVICE)
        self.wardrobe_data: Dict[str, Any] = {"items": [], "style_profile": None}
        self.load()

    def load(self):
        if os.path.exists(WARDROBE_FILE):
            try:
                with open(WARDROBE_FILE, "r", encoding="utf-8") as f:
                    self.wardrobe_data = json.load(f)
            except Exception as e:
                print(f"Error loading wardrobe data: {e}")
                self.wardrobe_data = {"items": [], "style_profile": None}

    def save(self):
        os.makedirs(os.path.dirname(WARDROBE_FILE), exist_ok=True)
        with open(WARDROBE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.wardrobe_data, f, indent=2, ensure_ascii=False)

    def scan_and_process(self, force_resegment: bool = False) -> Dict[str, Any]:
        """
        Scans clothes/ folder, performs garment detection & segmentation for new/modified images,
        computes Fashion-CLIP embeddings, and builds the user's style profile.
        """
        valid_exts = (".jpg", ".jpeg", ".png", ".webp")
        photo_paths = sorted([
            p for p in glob.glob(str(CLOTHES_DIR / "*"))
            if Path(p).suffix.lower() in valid_exts
        ])

        existing_by_source = {
            item["source_image"]: item for item in self.wardrobe_data.get("items", [])
        }

        updated_items = []
        vectors_for_profile = []

        print(f"[WardrobeService] Scanning {len(photo_paths)} photos in {CLOTHES_DIR}...")
        for p in photo_paths:
            filename = Path(p).name
            crop_filename = f"crop_{Path(p).stem}.jpg"
            crop_path = str(CROPS_DIR / crop_filename)

            need_segment = force_resegment or (filename not in existing_by_source) or (not os.path.exists(crop_path))
            
            if need_segment:
                print(f"  Segmenting garment from {filename} -> {crop_filename}...")
                try:
                    seg_result = self.segmenter.segment_image(p, crop_path)
                    print(f"  Embedding cropped garment {crop_filename} with Fashion-CLIP...")
                    embedding_vec = self.embedder.embed_image(crop_path)
                    
                    item = {
                        "id": Path(p).stem,
                        "source_image": filename,
                        "crop_filename": crop_filename,
                        "crop_url": f"/api/static/crops/{crop_filename}",
                        "source_url": f"/api/static/clothes/{filename}",
                        "category": seg_result["category"],
                        "colors": seg_result["colors"],
                        "aspect_ratio": seg_result["aspect_ratio"],
                        "crop_size": seg_result["crop_size"],
                        "embedding": embedding_vec.tolist()
                    }
                    updated_items.append(item)
                    vectors_for_profile.append(embedding_vec)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
            else:
                # Use existing item
                item = existing_by_source[filename]
                updated_items.append(item)
                if "embedding" in item:
                    vectors_for_profile.append(np.array(item["embedding"], dtype=np.float32))

        # Compute aggregate personal style profile
        if vectors_for_profile:
            style_profile_vec = self.embedder.compute_style_profile(vectors_for_profile)
            self.wardrobe_data["style_profile"] = style_profile_vec.tolist()
        else:
            self.wardrobe_data["style_profile"] = None

        self.wardrobe_data["items"] = updated_items
        self.wardrobe_data["total_garments"] = len(updated_items)
        self.save()
        
        return {
            "total_garments": len(updated_items),
            "processed_count": len(updated_items),
            "items": self.get_items_summary()
        }

    def get_items_summary(self) -> List[Dict[str, Any]]:
        """Return wardrobe items without bulky embedding vectors for lightweight JSON serialization."""
        summary = []
        for item in self.wardrobe_data.get("items", []):
            item_copy = {k: v for k, v in item.items() if k != "embedding"}
            summary.append(item_copy)
        return summary

    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        for item in self.wardrobe_data.get("items", []):
            if item["id"] == item_id or item["crop_filename"] == item_id or item["source_image"] == item_id:
                return item
        return None

    def get_style_profile_vector(self) -> Optional[np.ndarray]:
        profile = self.wardrobe_data.get("style_profile")
        if profile is not None:
            return np.array(profile, dtype=np.float32)
        return None
