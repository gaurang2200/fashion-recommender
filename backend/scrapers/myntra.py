import re
import json
import requests
from typing import List, Dict, Any
from backend.scrapers.base import BaseScraper

class MyntraScraper(BaseScraper):
    def __init__(self):
        super().__init__("Myntra", rate_limit_sec=1.5)
        self.base_url = "https://www.myntra.com"

    def scrape_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape Myntra category search."""
        category_map = {
            "tops": "women-tops",
            "dresses": "dresses",
            "bottoms": "women-trousers",
            "ethnic": "women-kurtas-kurtis-suits",
            "footwear": "women-footwear"
        }
        slug = category_map.get(category.lower(), "women-clothing")
        url = f"{self.base_url}/{slug}?f=Gender%3Amen%20women%2Cwomen&rawQuery={slug}"
        
        products = []
        try:
            self.sleep()
            headers = self.get_headers()
            res = self.session.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                start_idx = res.text.find("window.__myx = ")
                if start_idx != -1:
                    end_idx = res.text.find("</script>", start_idx)
                    script_content = res.text[start_idx + len("window.__myx = "):end_idx].strip()
                    if script_content.endswith(";"):
                        script_content = script_content[:-1].strip()
                    data = json.loads(script_content)
                    raw_items = data.get("searchData", {}).get("results", {}).get("products", [])
                    for item in raw_items[:limit]:
                        pid = str(item.get("productId", ""))
                        title = item.get("additionalInfo", item.get("productName", "Myntra Garment"))
                        brand = item.get("brand", "Myntra")
                        price = float(item.get("price", 1299))
                        mrp = float(item.get("mrp", price))
                        img_url = item.get("searchImage", "")
                        if img_url.startswith("http://"):
                            img_url = img_url.replace("http://", "https://")
                        landing_page = item.get("landingPageUrl", "")
                        prod_url = f"{self.base_url}/{landing_page}" if landing_page else url
                        
                        sizes_raw = item.get("sizes", "").split(",") if item.get("sizes") else ["S", "M", "L", "XL"]
                        
                        products.append(self.normalize_product(
                            product_id=pid,
                            title=title,
                            brand=brand,
                            category=category,
                            price=price,
                            original_price=mrp,
                            image_url=img_url,
                            product_url=prod_url,
                            sizes=sizes_raw
                        ))
        except Exception as e:
            print(f"[MyntraScraper] Live fetch info: {e}")
        return products

    def scrape_search(self, query: str, category: str = "tops", limit: int = 5) -> List[Dict[str, Any]]:
        """Scrape Myntra search results for a query."""
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f"{self.base_url}/search?q={encoded_query}"
        
        products = []
        try:
            self.sleep()
            headers = self.get_headers()
            res = self.session.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                start_idx = res.text.find("window.__myx = ")
                if start_idx != -1:
                    end_idx = res.text.find("</script>", start_idx)
                    script_content = res.text[start_idx + len("window.__myx = "):end_idx].strip()
                    if script_content.endswith(";"):
                        script_content = script_content[:-1].strip()
                    data = json.loads(script_content)
                    raw_items = data.get("searchData", {}).get("results", {}).get("products", [])
                    for item in raw_items[:limit]:
                        pid = str(item.get("productId", ""))
                        if not pid:
                            continue
                        title = item.get("additionalInfo", item.get("productName", "Myntra Garment"))
                        brand = item.get("brand", "Myntra")
                        price = float(item.get("price", 1299))
                        mrp = float(item.get("mrp", price))
                        img_url = item.get("searchImage", "")
                        if img_url.startswith("http://"):
                            img_url = img_url.replace("http://", "https://")
                        landing_page = item.get("landingPageUrl", "")
                        prod_url = f"{self.base_url}/{landing_page}" if landing_page else url
                        
                        sizes_raw = item.get("sizes", "").split(",") if item.get("sizes") else ["S", "M", "L", "XL"]
                        
                        products.append(self.normalize_product(
                            product_id=pid,
                            title=title,
                            brand=brand,
                            category=category,
                            price=price,
                            original_price=mrp,
                            image_url=img_url,
                            product_url=prod_url,
                            sizes=sizes_raw
                        ))
        except Exception as e:
            print(f"[MyntraScraper] Live search error for '{query}': {e}")
        return products

