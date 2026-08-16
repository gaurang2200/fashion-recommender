import time
import random
import requests
from typing import List, Dict, Any, Optional

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

class BaseScraper:
    def __init__(self, retailer_name: str, rate_limit_sec: float = 1.0):
        self.retailer_name = retailer_name
        self.rate_limit_sec = rate_limit_sec
        self.session = requests.Session()

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive"
        }

    def sleep(self):
        jitter = random.uniform(0.5, 1.5)
        time.sleep(self.rate_limit_sec * jitter)

    def normalize_product(
        self,
        product_id: str,
        title: str,
        brand: str,
        category: str,
        price: float,
        original_price: float,
        image_url: str,
        product_url: str,
        sizes: List[str],
        color: str = "Multicolor"
    ) -> Dict[str, Any]:
        discount_pct = 0
        if original_price > price and original_price > 0:
            discount_pct = int(round(((original_price - price) / original_price) * 100))

        return {
            "id": f"{self.retailer_name.lower().replace(' ', '_')}_{product_id}",
            "title": title.strip(),
            "brand": brand.strip(),
            "retailer": self.retailer_name,
            "category": category.lower(),
            "price": float(price),
            "original_price": float(original_price if original_price > 0 else price),
            "discount_pct": discount_pct,
            "image_url": image_url,
            "product_url": product_url,
            "sizes": [s.strip().upper() for s in sizes] if sizes else ["S", "M", "L"],
            "color": color,
            "in_stock": True
        }
