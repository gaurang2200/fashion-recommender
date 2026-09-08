export interface WardrobeItem {
  id: string;
  source_image: string;
  crop_filename: string;
  crop_url: string;
  source_url: string;
  category: string;
  colors: string[];
  aspect_ratio: number;
  crop_size: [number, number];
}

export interface Product {
  id: string;
  title: string;
  brand: string;
  retailer: string;
  category: string;
  price: number;
  original_price: number;
  discount_pct: number;
  image_url: string;
  product_url: string;
  sizes: string[];
  color: string;
  in_stock: boolean;
  rating?: number;
  review_count?: number;
  similarity_score?: number;
  preference_boost?: number;
  final_score?: number;
  match_percentage?: number;
  raw_similarity_pct?: number;
  user_feedback?: "liked" | "disliked" | null;
  is_new?: boolean;
}

export interface FilterOptions {
  garment_id: string;
  category: string;
  retailer: string;
  min_price: number | null;
  max_price: number | null;
  size: string;
  sort_by: string;
  preference_weight: number;
}

export interface StyleInsightsData {
  total_wardrobe_pieces: number;
  category_distribution: Record<string, number>;
  signature_colors: string[];
  favorite_brands: Record<string, number>;
  preferred_retailers: Record<string, number>;
  liked_count: number;
  disliked_count: number;
}
