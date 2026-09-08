import React from "react";
import type { Product } from "../types";
import { ThumbsUp, ThumbsDown, ArrowUpRight } from "lucide-react";

interface ProductCardProps {
  product: Product;
  onFeedback: (productId: string, isLike: boolean) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onFeedback }) => {
  const isLiked = product.user_feedback === "liked";
  const isDisliked = product.user_feedback === "disliked";

  const getRetailerColor = (ret: string) => {
    switch (ret.toLowerCase()) {
      case "ajio":
        return "bg-slate-900 text-slate-100 border-slate-900";
      case "myntra":
        return "bg-rose-50 text-rose-700 border-rose-200";
      case "max fashion":
        return "bg-blue-50 text-blue-700 border-blue-200";
      default:
        return "bg-neutral-100 text-neutral-800 border-neutral-200";
    }
  };

  // Color gradient based on match percentage
  const getMatchScoreBadge = (score?: number) => {
    if (!score) return null;
    const pct = Math.round(score);
    let color = "text-neutral-800 bg-neutral-100";
    if (pct >= 85) color = "text-emerald-800 bg-emerald-50 border-emerald-200";
    else if (pct >= 70) color = "text-amber-800 bg-amber-50 border-amber-200";
    
    return (
      <div className={`px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase border ${color}`}>
        {pct}% Style Match
      </div>
    );
  };

  return (
    <div className="editorial-card group flex flex-col h-full bg-white relative overflow-hidden">
      {/* Product Image Panel */}
      <div className="relative aspect-[3/4] w-full overflow-hidden bg-neutral-50">
        <img
          src={product.image_url}
          alt={product.title}
          className="h-full w-full object-cover object-top transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />

        {/* NEW badge */}
        {product.is_new && (
          <div className="absolute top-3 left-3 px-2 py-0.5 bg-neutral-900 text-amber-300 text-[9px] font-bold tracking-widest uppercase rounded-sm shadow-sm z-10 border border-amber-400/30 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            NEW
          </div>
        )}

        {/* Link Out overlay button */}
        <a
          href={product.product_url}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute top-3 right-3 p-2 bg-white rounded-full text-neutral-700 hover:text-neutral-900 hover:bg-neutral-50 transition-all opacity-0 group-hover:opacity-100 duration-200 border border-neutral-100 shadow-sm"
          title="View on Store"
        >
          <ArrowUpRight className="w-4 h-4" />
        </a>

        {/* Retailer badge */}
        <div className={`absolute bottom-3 left-3 px-2 py-0.5 border text-[9px] font-semibold tracking-wider uppercase rounded-sm ${getRetailerColor(product.retailer)}`}>
          {product.retailer}
        </div>
      </div>

      {/* Product Info */}
      <div className="p-4 flex flex-col flex-grow">
        <div className="flex justify-between items-start mb-1">
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold truncate max-w-[70%]">
            {product.brand}
          </span>
          {getMatchScoreBadge(product.match_percentage)}
        </div>

        <a
          href={product.product_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-medium text-neutral-800 line-clamp-2 hover:underline mb-3"
        >
          {product.title}
        </a>

        <div className="mt-auto">
          {/* Price Layout */}
          <div className="flex items-baseline gap-2 mb-3">
            <span className="text-sm font-semibold text-neutral-900">
              ₹{product.price}
            </span>
            {product.original_price > product.price && (
              <>
                <span className="text-[11px] text-neutral-400 line-through">
                  ₹{product.original_price}
                </span>
                <span className="text-[10px] font-bold text-rose-500 uppercase tracking-wider">
                  ({product.discount_pct}% OFF)
                </span>
              </>
            )}
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-neutral-100">
            {/* Sizes in stock */}
            <span className="text-[9px] uppercase tracking-widest text-neutral-400 font-medium">
              Sizes: {product.sizes.slice(0, 4).join(", ")}
              {product.sizes.length > 4 ? "+" : ""}
            </span>

            {/* Like/Dislike Actions */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => onFeedback(product.id, false)}
                className={`p-1.5 rounded-sm border transition-all cursor-pointer ${
                  isDisliked
                    ? "bg-red-50 border-red-200 text-red-500"
                    : "border-transparent text-neutral-400 hover:text-red-500 hover:bg-neutral-50"
                }`}
                title="Not my style"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onFeedback(product.id, true)}
                className={`p-1.5 rounded-sm border transition-all cursor-pointer ${
                  isLiked
                    ? "bg-emerald-50 border-emerald-200 text-emerald-600"
                    : "border-transparent text-neutral-400 hover:text-emerald-600 hover:bg-neutral-50"
                }`}
                title="Love this style"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
