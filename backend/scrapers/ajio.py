import re
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from backend.scrapers.base import BaseScraper

class AjioScraper(BaseScraper):
    def __init__(self):
        super().__init__("Ajio", rate_limit_sec=1.5)
        self.base_url = "https://www.ajio.com"

    def scrape_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape Ajio for specific women fashion categories."""
        category_map = {
            "tops": "women-tops",
            "dresses": "women-dresses",
            "bottoms": "women-trousers-pants",
            "ethnic": "women-kurtas-kurtis",
            "footwear": "women-footwear"
        }
        slug = category_map.get(category.lower(), "women-clothing")
        url = f"{self.base_url}/s/{slug}?format=json"
        
        products = []
        try:
            self.sleep()
            headers = self.get_headers()
            headers["Accept"] = "application/json"
            res = self.session.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                raw_items = data.get("products", [])
                for item in raw_items[:limit]:
                    pid = str(item.get("code", item.get("fnlColorVariantData", {}).get("colorGroup", "")))
                    title = item.get("name", "Fashion Item")
                    brand = item.get("brandName", "AJIO")
                    price_data = item.get("price", {})
                    price = float(price_data.get("value", 999))
                    was_price = float(item.get("wasPriceData", {}).get("value", price))
                    img_url = item.get("images", [{}])[0].get("url", "")
                    prod_url = f"{self.base_url}{item.get('url', '')}"
                    
                    products.append(self.normalize_product(
                        product_id=pid,
                        title=title,
                        brand=brand,
                        category=category,
                        price=price,
                        original_price=was_price,
                        image_url=img_url,
                        product_url=prod_url,
                        sizes=["XS", "S", "M", "L", "XL"]
                    ))
        except Exception as e:
            print(f"[AjioScraper] Live fetch info: {e}")
        return products

    def scrape_search(self, query: str, category: str = "tops", limit: int = 5) -> List[Dict[str, Any]]:
        """Scrape Ajio search results for a query."""
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f"{self.base_url}/search/?text={encoded_query}&format=json"
        
        products = []
        try:
            self.sleep()
            headers = self.get_headers()
            headers["Accept"] = "application/json"
            res = self.session.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                raw_items = data.get("products", [])
                for item in raw_items[:limit]:
                    pid = str(item.get("code", item.get("fnlColorVariantData", {}).get("colorGroup", "")))
                    if not pid:
                        continue
                    title = item.get("name", "Fashion Item")
                    brand = item.get("brandName", "AJIO")
                    price_data = item.get("price", {})
                    price = float(price_data.get("value", 999))
                    was_price = float(item.get("wasPriceData", {}).get("value", price))
                    img_url = item.get("images", [{}])[0].get("url", "")
                    prod_url = f"{self.base_url}{item.get('url', '')}"
                    
                    products.append(self.normalize_product(
                        product_id=pid,
                        title=title,
                        brand=brand,
                        category=category,
                        price=price,
                        original_price=was_price,
                        image_url=img_url,
                        product_url=prod_url,
                        sizes=["XS", "S", "M", "L", "XL"]
                    ))
        except Exception as e:
            print(f"[AjioScraper] Live search error for '{query}': {e}")
        return products

