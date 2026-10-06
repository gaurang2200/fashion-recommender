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
        tmp_file = f"{WARDROBE_FILE}.{os.getpid()}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self.wardrobe_data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, WARDROBE_FILE)

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
        new_items = []
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
                    new_items.append(item)
                    vectors_for_profile.append(embedding_vec)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
            else:
                # Use existing item
                item = existing_by_source[filename]
                updated_items.append(item)
                if "embedding" in item:
                    vectors_for_profile.append(np.array(item["embedding"], dtype=np.float32))

        # Compute aggregate personal style profile & style clusters
        if vectors_for_profile:
            style_profile_vec = self.embedder.compute_style_profile(vectors_for_profile)
            self.wardrobe_data["style_profile"] = style_profile_vec.tolist()
            clusters = self.compute_style_clusters(vectors_for_profile)
            self.wardrobe_data["style_clusters"] = [c.tolist() for c in clusters]
        else:
            self.wardrobe_data["style_profile"] = None
            self.wardrobe_data["style_clusters"] = []

        self.wardrobe_data["items"] = updated_items
        self.wardrobe_data["total_garments"] = len(updated_items)
        self.save()
        
        return {
            "total_garments": len(updated_items),
            "new_items_count": len(new_items),
            "new_items": [{k: v for k, v in it.items() if k != "embedding"} for it in new_items],
            "items": self.get_items_summary()
        }

    def compute_style_clusters(self, vectors: List[np.ndarray], max_clusters: int = 3) -> List[np.ndarray]:
        """
        Group wardrobe vectors into distinct style clusters using NumPy K-Means.
        Returns a list of L2-normalized cluster centroid vectors.
        """
        if not vectors:
            return []
        
        vec_matrix = np.array(vectors, dtype=np.float32)
        n_samples = len(vec_matrix)
        
        if n_samples <= 2:
            clusters = []
            for i in range(n_samples):
                v_norm = np.linalg.norm(vec_matrix[i])
                clusters.append((vec_matrix[i] / (v_norm if v_norm > 0 else 1.0)).astype(np.float32))
            return clusters
        
        k = min(max_clusters, max(2, n_samples // 3))
        
        # Initialize K centroids using farthest-point sampling
        centroids = [vec_matrix[0]]
        while len(centroids) < k:
            dists = np.array([min(np.linalg.norm(v - c) for c in centroids) for v in vec_matrix])
            farthest_idx = int(np.argmax(dists))
            centroids.append(vec_matrix[farthest_idx])
            
        centroids = np.array(centroids, dtype=np.float32)
        
        # Run K-Means iterations
        for _ in range(25):
            norms = np.linalg.norm(centroids, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            norm_centroids = centroids / norms
            
            sims = np.dot(vec_matrix, norm_centroids.T)
            assignments = np.argmax(sims, axis=1)
            
            new_centroids = []
            for i in range(k):
                members = vec_matrix[assignments == i]
                if len(members) > 0:
                    c_mean = np.mean(members, axis=0)
                    c_norm = np.linalg.norm(c_mean)
                    if c_norm > 0:
                        c_mean = c_mean / c_norm
                    new_centroids.append(c_mean)
                else:
                    new_centroids.append(norm_centroids[i])
            centroids = np.array(new_centroids, dtype=np.float32)
            
        result_clusters = []
        for c in centroids:
            c_norm = np.linalg.norm(c)
            if c_norm > 0:
                result_clusters.append((c / c_norm).astype(np.float32))
            else:
                result_clusters.append(c.astype(np.float32))
        return result_clusters

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

    def get_style_cluster_vectors(self) -> List[np.ndarray]:
        """
        Return normalized cluster centroid vectors representing distinct style clusters.
        """
        clusters = self.wardrobe_data.get("style_clusters")
        if clusters and len(clusters) > 0:
            return [np.array(c, dtype=np.float32) for c in clusters]
        
        # If style profile single vector exists
        profile = self.get_style_profile_vector()
        if profile is not None:
            return [profile]
            
        # Fallback: compute from wardrobe items directly
        item_vecs = []
        for item in self.wardrobe_data.get("items", []):
            if "embedding" in item:
                item_vecs.append(np.array(item["embedding"], dtype=np.float32))
        if item_vecs:
            return self.compute_style_clusters(item_vecs)
            
        return []

