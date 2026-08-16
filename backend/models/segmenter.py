import os
import glob
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np
from rembg import remove, new_session
from typing import List, Dict, Any, Optional
import colorsys

class GarmentSegmenter:
    """
    Garment detection and segmentation engine.
    Uses U2-Net/rembg for high-precision garment isolation from cluttered user photos,
    followed by bounding box extraction, smart centering, and background normalization.
    """
    def __init__(self, model_name: str = "u2net"):
        self.model_name = model_name
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = new_session(self.model_name)
        return self._session

    def extract_dominant_colors(self, image: Image.Image, num_colors: int = 3) -> List[str]:
        """Extract dominant hex colors from non-transparent pixels."""
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Resize for fast color quantization
        small_img = image.resize((100, 100))
        np_img = np.array(small_img)
        
        # Filter non-transparent pixels (alpha > 50)
        mask = np_img[:, :, 3] > 50
        rgb_pixels = np_img[:, :, :3][mask]
        
        if len(rgb_pixels) == 0:
            return ["#333333"]
            
        # K-means or simple histogram binning
        from collections import Counter
        # Quantize to 32 bins
        quantized = (rgb_pixels // 32) * 32 + 16
        color_tuples = [tuple(c) for c in quantized]
        counts = Counter(color_tuples).most_common(num_colors)
        
        hex_colors = []
        for (r, g, b), _ in counts:
            hex_colors.append(f"#{int(r):02x}{int(g):02x}{int(b):02x}")
        return hex_colors

    def detect_category(self, filename: str, aspect_ratio: float, dominant_colors: List[str]) -> str:
        """Infer clothing category from filename and garment geometry."""
        fn_lower = filename.lower()
        if any(k in fn_lower for k in ["dress", "gown", "frock"]):
            return "dresses"
        elif any(k in fn_lower for k in ["top", "shirt", "blouse", "tee", "crop"]):
            return "tops"
        elif any(k in fn_lower for k in ["pant", "jean", "trouser", "skirt", "short", "bottom"]):
            return "bottoms"
        elif any(k in fn_lower for k in ["kurta", "kurti", "saree", "ethnic", "lehenga", "suit"]):
            return "ethnic"
        elif any(k in fn_lower for k in ["shoe", "sandal", "heel", "sneaker", "footwear"]):
            return "footwear"
        
        # Aspect ratio heuristics: tall garments are often dresses or ethnic wear
        if aspect_ratio > 1.5:
            return "dresses"
        elif aspect_ratio < 0.9:
            return "tops"
        else:
            return "dresses"

    def segment_image(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Takes a raw photo, removes background clutter, extracts garment bounding box,
        centers it on a clean white/transparent canvas, and saves the crop.
        """
        img = Image.open(input_path).convert("RGB")
        orig_w, orig_h = img.size
        
        # Max resolution for segmentation speed & memory efficiency
        max_dim = 1200
        if max(orig_w, orig_h) > max_dim:
            scale = max_dim / max(orig_w, orig_h)
            new_size = (int(orig_w * scale), int(orig_h * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Run background removal
        segmented = remove(img, session=self.session)
        
        # Find alpha bounding box
        alpha = np.array(segmented)[:, :, 3]
        pos_pixels = np.where(alpha > 20)
        
        if len(pos_pixels[0]) > 0:
            ymin, ymax = np.min(pos_pixels[0]), np.max(pos_pixels[0])
            xmin, xmax = np.min(pos_pixels[1]), np.max(pos_pixels[1])
            
            # Add padding
            pad_y = int((ymax - ymin) * 0.05)
            pad_x = int((xmax - xmin) * 0.05)
            ymin = max(0, ymin - pad_y)
            ymax = min(segmented.height, ymax + pad_y)
            xmin = max(0, xmin - pad_x)
            xmax = min(segmented.width, xmax + pad_x)
            
            cropped = segmented.crop((xmin, ymin, xmax, ymax))
        else:
            cropped = segmented
            ymin, ymax, xmin, xmax = 0, segmented.height, 0, segmented.width
            
        # Composite on pure white square canvas for clean editorial presentation & embedding
        crop_w, crop_h = cropped.size
        square_size = max(crop_w, crop_h) + 40
        canvas = Image.new("RGBA", (square_size, square_size), (255, 255, 255, 255))
        offset = ((square_size - crop_w) // 2, (square_size - crop_h) // 2)
        canvas.paste(cropped, offset, cropped)
        
        # Save as PNG
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        canvas.convert("RGB").save(output_path, "JPEG", quality=95)
        
        aspect = crop_h / max(crop_w, 1)
        colors = self.extract_dominant_colors(cropped)
        filename = Path(input_path).name
        category = self.detect_category(filename, aspect, colors)
        
        return {
            "source_image": filename,
            "crop_path": output_path,
            "crop_filename": Path(output_path).name,
            "aspect_ratio": round(aspect, 2),
            "category": category,
            "colors": colors,
            "crop_size": [crop_w, crop_h],
            "bounding_box": [int(xmin), int(ymin), int(xmax), int(ymax)]
        }
