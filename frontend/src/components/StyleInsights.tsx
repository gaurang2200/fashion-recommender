import React, { useState, useEffect } from "react";
import type { StyleInsightsData, Product } from "../types";
import { fetchStyleInsights, fetchLikedProducts, submitFeedback } from "../api";
import { ProductCard } from "./ProductCard";
import { Sparkles, BarChart2, Heart, Award } from "lucide-react";

interface StyleInsightsProps {
  feedbackRefreshTrigger: number;
}

export const StyleInsights: React.FC<StyleInsightsProps> = ({ feedbackRefreshTrigger }) => {
  const [insights, setInsights] = useState<StyleInsightsData | null>(null);
  const [likedProducts, setLikedProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingLikes, setLoadingLikes] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setLoadingLikes(true);
    try {
      const data = await fetchStyleInsights();
      setInsights(data);
    } catch (err) {
      console.error("Failed to load insights:", err);
    } finally {
      setLoading(false);
    }

    try {
      const likesRes = await fetchLikedProducts();
      setLikedProducts(likesRes.items);
    } catch (err) {
      console.error("Failed to load liked products:", err);
    } finally {
      setLoadingLikes(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [feedbackRefreshTrigger]);

  const handleUnlike = async (productId: string, isLike: boolean) => {
    try {
      await submitFeedback(productId, isLike);
      if (!isLike) {
        setLikedProducts(prev => prev.filter(p => p.id !== productId));
      } else {
        // Toggle or re-fetch
        const likesRes = await fetchLikedProducts();
        setLikedProducts(likesRes.items);
      }
      const data = await fetchStyleInsights();
      setInsights(data);
    } catch (err) {
      console.error("Failed to update feedback:", err);
    }
  };

  if (loading || !insights) {
    return (
      <div className="w-full py-20 flex flex-col items-center justify-center text-neutral-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-neutral-800 mb-4"></div>
        <span className="text-xs uppercase tracking-widest font-medium">Analyzing aesthetic parameters...</span>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-8">
      {/* Editorial Header */}
      <div className="bg-white border border-neutral-200 p-6 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex flex-col">
          <h2 className="editorial-serif text-lg font-medium text-neutral-800 uppercase tracking-widest flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-500" />
            My Aesthetic Insights
          </h2>
          <p className="text-xs text-neutral-400 font-light mt-1 max-w-xl">
            Statistical breakdown of your scanned wardrobe silhouette, color profile, and active style preferences.
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        {/* Total stats card */}
        <div className="bg-white border border-neutral-200 p-6 flex flex-col items-center justify-center text-center">
          <BarChart2 className="w-8 h-8 text-neutral-800 mb-3" />
          <span className="text-3xl font-semibold text-neutral-900">{insights.total_wardrobe_pieces}</span>
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold mt-2">
            Wardrobe Pieces Scanned
          </span>
        </div>

        {/* Favorite Retailer stats */}
        <div className="bg-white border border-neutral-200 p-6 flex flex-col items-center justify-center text-center">
          <Award className="w-8 h-8 text-neutral-800 mb-3" />
          <span className="text-xl font-semibold text-neutral-900 truncate max-w-full">
            {Object.keys(insights.preferred_retailers)[0] || "None Yet"}
          </span>
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold mt-2">
            Preferred Retailer
          </span>
        </div>

        {/* Liked Count stats */}
        <div className="bg-white border border-neutral-200 p-6 flex flex-col items-center justify-center text-center">
          <Heart className="w-8 h-8 text-rose-500 mb-3" />
          <span className="text-3xl font-semibold text-neutral-900">{insights.liked_count}</span>
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold mt-2">
            Style Catalog Likes
          </span>
        </div>

        {/* Disliked Count stats */}
        <div className="bg-white border border-neutral-200 p-6 flex flex-col items-center justify-center text-center">
          <Heart className="w-8 h-8 text-neutral-300 rotate-180 mb-3" />
          <span className="text-3xl font-semibold text-neutral-900">{insights.disliked_count}</span>
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold mt-2">
            Style Catalog Dislikes
          </span>
        </div>
      </div>

      {/* My Liked Collection Grid */}
      <div className="bg-white border border-neutral-200 p-6 flex flex-col gap-6">
        <div className="flex justify-between items-baseline border-b border-neutral-100 pb-3">
          <div>
            <h3 className="editorial-serif text-base font-semibold uppercase tracking-widest text-neutral-800 flex items-center gap-2">
              <Heart className="w-4 h-4 text-rose-500 fill-rose-500" />
              My Liked Collection
            </h3>
            <p className="text-xs text-neutral-400 font-light mt-1">
              All dresses and garments you marked thumbs-up while exploring style recommendations.
            </p>
          </div>
          <span className="text-xs text-neutral-500 font-medium">
            {likedProducts.length} {likedProducts.length === 1 ? "Item" : "Items"}
          </span>
        </div>

        {loadingLikes ? (
          <div className="py-12 flex justify-center items-center text-neutral-400 text-xs uppercase tracking-widest font-medium">
            Loading collection...
          </div>
        ) : likedProducts.length === 0 ? (
          <div className="py-12 text-center text-neutral-400 bg-neutral-50 border border-neutral-100 p-6">
            <Heart className="w-8 h-8 mx-auto mb-2 opacity-40 text-neutral-400" />
            <p className="text-sm font-medium text-neutral-700">No Liked Dresses Yet</p>
            <p className="text-xs font-light mt-1 text-neutral-500">
              Click the thumbs-up icon on any dress in the recommendation feed or catalog explorer to save it here!
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 md:gap-6">
            {likedProducts.map(product => (
              <ProductCard
                key={product.id}
                product={product}
                onFeedback={handleUnlike}
              />
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Category Breakdown */}
        <div className="bg-white border border-neutral-200 p-6">
          <h3 className="editorial-serif text-sm font-semibold uppercase tracking-widest mb-6 text-neutral-800 border-b border-neutral-100 pb-2">
            Wardrobe Category Breakdown
          </h3>
          <div className="flex flex-col gap-4">
            {Object.entries(insights.category_distribution).map(([cat, count]) => {
              const pct = insights.total_wardrobe_pieces > 0
                ? Math.round((count / insights.total_wardrobe_pieces) * 100)
                : 0;
              return (
                <div key={cat} className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-xs font-semibold text-neutral-700">
                    <span className="uppercase tracking-wider">{cat}</span>
                    <span>{count} items ({pct}%)</span>
                  </div>
                  <div className="w-full bg-neutral-100 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-neutral-800 h-full rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Color Palette Analysis */}
        <div className="bg-white border border-neutral-200 p-6">
          <h3 className="editorial-serif text-sm font-semibold uppercase tracking-widest mb-6 text-neutral-800 border-b border-neutral-100 pb-2">
            Signature Color Palette
          </h3>
          <p className="text-xs text-neutral-400 font-light mb-6">
            Extracted dominant shades from your wardrobe items. Hover for hex codes.
          </p>
          <div className="grid grid-cols-4 sm:grid-cols-8 gap-4">
            {insights.signature_colors.map((color, index) => (
              <div key={index} className="flex flex-col items-center gap-2">
                <div
                  className="w-12 h-12 rounded-full border border-neutral-200 shadow-sm cursor-help hover:scale-105 transition-all"
                  style={{ backgroundColor: color }}
                  title={color}
                />
                <span className="text-[10px] font-mono text-neutral-500">{color}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

