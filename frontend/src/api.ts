import type { WardrobeItem, Product, FilterOptions, StyleInsightsData } from "./types";

const API_BASE = "http://localhost:8000/api";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchMetadata() {
  const res = await fetch(`${API_BASE}/meta`);
  return res.json();
}

export async function fetchWardrobe(): Promise<{ total: number; has_style_profile: boolean; items: WardrobeItem[] }> {
  const res = await fetch(`${API_BASE}/wardrobe`);
  return res.json();
}

export async function rescanWardrobe(force: boolean = false): Promise<any> {
  const res = await fetch(`${API_BASE}/wardrobe/rescan?force=${force}`, {
    method: "POST"
  });
  return res.json();
}

export async function fetchRecommendations(filters: FilterOptions & { top_k?: number }): Promise<{
  total_matches: number;
  source_garment: WardrobeItem | null;
  products: Product[];
}> {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters)
  });
  return res.json();
}

export async function submitFeedback(productId: string, isLike: boolean, productData?: Product): Promise<any> {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      product_id: productId,
      is_like: isLike,
      product_data: productData
    })
  });
  return res.json();
}

export async function fetchCatalog(category: string = "all", retailer: string = "all", limit: number = 60, offset: number = 0): Promise<{
  total: number;
  items: Product[];
}> {
  const res = await fetch(`${API_BASE}/catalog?category=${category}&retailer=${retailer}&limit=${limit}&offset=${offset}`);
  return res.json();
}

export async function triggerScrape(params: { category: string; retailer: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/catalog/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params)
  });
  return res.json();
}

export async function fetchStyleInsights(): Promise<StyleInsightsData> {
  const res = await fetch(`${API_BASE}/style-insights`);
  return res.json();
}

export async function fetchCatalogStatus(): Promise<{ is_indexing: boolean; total_products: number; index_size: number }> {
  const res = await fetch(`${API_BASE}/catalog/status`);
  return res.json();
}

export async function fetchLikedProducts(): Promise<{ total: number; items: Product[] }> {
  const res = await fetch(`${API_BASE}/likes`);
  return res.json();
}

