import React, { useState, useEffect } from "react";
import type { Product, WardrobeItem, FilterOptions } from "../types";
import { ProductCard } from "./ProductCard";
import { FilterBar } from "./FilterBar";
import { Sparkles, ShoppingBag } from "lucide-react";
import { fetchMetadata, fetchRecommendations, getImageUrl } from "../api";


interface RecommendViewProps {
  selectedGarment: WardrobeItem | null;
  onFeedback: (productId: string, isLike: boolean, productData?: Product) => void;
  feedbackRefreshTrigger: number;
}

export const RecommendView: React.FC<RecommendViewProps> = ({
  selectedGarment,
  onFeedback,
  feedbackRefreshTrigger: _feedbackRefreshTrigger
}) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [meta, setMeta] = useState<any>({
    categories: [],
    retailers: [],
    sizes: [],
    price_bounds: { min: 0, max: 10000 },
    sort_options: []
  });
  const [filters, setFilters] = useState<FilterOptions>({
    garment_id: "all",
    category: "all",
    retailer: "all",
    min_price: null,
    max_price: null,
    size: "all",
    sort_by: "relevance",
    preference_weight: 0.25
  });
  
  const [loading, setLoading] = useState(false);
  const [pageSize, setPageSize] = useState(15);
  const [totalMatches, setTotalMatches] = useState(0);

  // Load categories, sizes, retailers metadata
  useEffect(() => {
    async function loadMeta() {
      try {
        const data = await fetchMetadata();
        setMeta(data);
      } catch (err) {
        console.error("Failed to load metadata:", err);
      }
    }
    loadMeta();
  }, []);

  // Update query target when selection changes
  useEffect(() => {
    setFilters(prev => ({
      ...prev,
      garment_id: selectedGarment ? selectedGarment.id : "all",
      // Auto-set category when choosing a garment to maximize relevance
      category: selectedGarment ? selectedGarment.category : "all"
    }));
    setPageSize(15);
  }, [selectedGarment]);

  // Query recommendations (Note: removed feedbackRefreshTrigger so liked items stay in place without jumbling grid)
  useEffect(() => {
    let active = true;
    async function getRecs() {
      setLoading(true);
      try {
        const data = await fetchRecommendations({
          ...filters,
          top_k: pageSize + 10 // Fetch slightly more to account for filters
        });
        if (active) {
          setProducts(data.products.slice(0, pageSize));
          setTotalMatches(data.total_matches);
        }
      } catch (err) {
        console.error("Failed to load recommendations:", err);
      } finally {
        if (active) setLoading(false);
      }
    }
    getRecs();
    return () => {
      active = false;
    };
  }, [filters, pageSize]);

  const handleProductFeedback = (productId: string, isLike: boolean) => {
    // In-place optimistic feedback so card position never shifts or jumbles
    setProducts(prev => prev.map(p => {
      if (p.id === productId) {
        const isCurrentlyLiked = p.user_feedback === "liked";
        const isCurrentlyDisliked = p.user_feedback === "disliked";
        let newFeedback: "liked" | "disliked" | null = isLike ? "liked" : "disliked";
        if ((isLike && isCurrentlyLiked) || (!isLike && isCurrentlyDisliked)) {
          newFeedback = null;
        }
        return { ...p, user_feedback: newFeedback as any };
      }
      return p;
    }));

    const targetProduct = products.find(p => p.id === productId);
    onFeedback(productId, isLike, targetProduct);
  };

  const loadMore = () => {
    setPageSize(prev => prev + 15);
  };

  return (
    <div className="w-full flex flex-col gap-8">
      {/* Current Query Target Header */}
      <div className="p-6 bg-neutral-900 text-white flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          {selectedGarment ? (
            <div className="relative w-16 h-16 bg-neutral-800 border border-neutral-700 overflow-hidden flex-shrink-0">
              <img
                src={getImageUrl(selectedGarment.crop_url)}
                alt="Selected item"
                className="w-full h-full object-cover object-center"
              />
            </div>
          ) : (
            <div className="w-16 h-16 bg-neutral-800 border border-neutral-700 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-6 h-6 text-amber-300" />
            </div>
          )}
          <div>
            <h3 className="editorial-serif text-lg tracking-wider font-medium">
              {selectedGarment ? `Matching: ${selectedGarment.source_image.replace(/\.[^/.]+$/, "")}` : "Wardrobe Style Matching"}
            </h3>
            <p className="text-xs text-neutral-400 font-light mt-1 max-w-xl">
              {selectedGarment
                ? `Inferred category: ${selectedGarment.category}. Recommendations are customized based on the shape, pattern, and color of this item.`
                : "Scanned all your wardrobe garments. Showing recommendations fitting your aggregated style profile."}
            </p>
          </div>
        </div>
        
        {selectedGarment && (
          <div className="flex gap-2.5">
            <span className="text-[10px] uppercase tracking-widest font-semibold text-neutral-400">
              Colors:
            </span>
            <div className="flex gap-1.5">
              {selectedGarment.colors.map((c, i) => (
                <div
                  key={i}
                  className="w-4 h-4 rounded-full border border-neutral-700"
                  style={{ backgroundColor: c }}
                  title={c}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filter panel */}
      <FilterBar
        filters={filters}
        setFilters={setFilters}
        categories={meta.categories}
        retailers={meta.retailers}
        sizes={meta.sizes}
        priceBounds={meta.price_bounds}
        sortOptions={meta.sort_options}
      />

      {/* Recommended product feed */}
      <div>
        <div className="flex justify-between items-baseline mb-6 border-b border-neutral-200 pb-3">
          <h2 className="editorial-serif text-lg font-medium text-neutral-800 uppercase tracking-widest">
            Matched Retailer Finds
          </h2>
          <span className="text-xs text-neutral-400 font-medium">
            Showing {products.length} of {totalMatches} matches
          </span>
        </div>

        {loading && products.length === 0 ? (
          <div className="w-full py-20 flex flex-col items-center justify-center text-neutral-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-neutral-800 mb-4"></div>
            <span className="text-xs uppercase tracking-widest font-medium">Analyzing Style Vectors...</span>
          </div>
        ) : products.length === 0 ? (
          <div className="w-full py-20 bg-white border border-neutral-200 text-center text-neutral-400">
            <ShoppingBag className="w-8 h-8 mx-auto mb-3 opacity-60" />
            <p className="text-sm font-medium">No matching products found.</p>
            <p className="text-xs font-light mt-1">Try widening your price range or clearing filters.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-10">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 md:gap-6">
              {products.map(p => (
                <ProductCard key={p.id} product={p} onFeedback={handleProductFeedback} />
              ))}
            </div>

            {/* Load more button */}
            {products.length < totalMatches && (
              <div className="flex justify-center mt-4">
                <button
                  onClick={loadMore}
                  disabled={loading}
                  className="editorial-button-outline px-8 py-3 font-semibold text-xs tracking-widest cursor-pointer hover:border-neutral-900"
                >
                  {loading ? "Loading matches..." : "Load More Style Matches"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

