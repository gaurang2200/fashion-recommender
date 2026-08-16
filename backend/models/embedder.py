import os
import torch
from PIL import Image
import numpy as np
from typing import List, Union
from transformers import CLIPProcessor, CLIPModel

class FashionEmbedder:
    """
    Fashion-CLIP embedding engine for computing 512-dimensional normalized vectors
    representing garment style, silhouette, pattern, texture, and color.
    """
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", device: str = "cpu"):
        self.device = device
        self.model_name = model_name
        self._model = None
        self._processor = None

    @property
    def model(self):
        if self._model is None:
            print(f"Loading CLIP model '{self.model_name}' on {self.device}...")
            self._model = CLIPModel.from_pretrained(self.model_name).to(self.device)
            self._model.eval()
        return self._model

    @property
    def processor(self):
        if self._processor is None:
            self._processor = CLIPProcessor.from_pretrained(self.model_name)
        return self._processor

    def embed_image(self, image: Union[Image.Image, str]) -> np.ndarray:
        """Embed a single image to a 512-dim L2-normalized float32 vector."""
        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        elif image.mode != "RGB":
            image = image.convert("RGB")

        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            if hasattr(image_features, "pooler_output"):
                image_features = image_features.pooler_output
            # L2 Normalize
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            vector = image_features.cpu().numpy().astype(np.float32)[0]
        return vector

    def embed_images_batch(self, images: List[Union[Image.Image, str]], batch_size: int = 16) -> np.ndarray:
        """Embed a batch of images to an (N, 512) normalized matrix."""
        all_vectors = []
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            pil_batch = []
            for img in batch:
                if isinstance(img, str):
                    pil_batch.append(Image.open(img).convert("RGB"))
                else:
                    pil_batch.append(img.convert("RGB"))
                    
            inputs = self.processor(images=pil_batch, return_tensors="pt").to(self.device)
            with torch.no_grad():
                features = self.model.get_image_features(**inputs)
                if hasattr(features, "pooler_output"):
                    features = features.pooler_output
                features = features / features.norm(p=2, dim=-1, keepdim=True)
                all_vectors.append(features.cpu().numpy().astype(np.float32))
                
        if len(all_vectors) == 0:
            return np.empty((0, 512), dtype=np.float32)
        return np.vstack(all_vectors)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a search query text into the shared 512-dim fashion embedding space."""
        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            if hasattr(text_features, "pooler_output"):
                text_features = text_features.pooler_output
            text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            vector = text_features.cpu().numpy().astype(np.float32)[0]
        return vector

    def compute_style_profile(self, vectors: List[np.ndarray]) -> np.ndarray:
        """
        Aggregate multiple garment vectors into a unified style profile vector
        representing the user's overall personal aesthetic.
        """
        if not vectors:
            return np.zeros(512, dtype=np.float32)
        mean_vec = np.mean(vectors, axis=0)
        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm
        return mean_vec.astype(np.float32)
