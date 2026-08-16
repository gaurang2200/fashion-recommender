import React, { useState, useEffect } from "react";
import type { StyleInsightsData } from "../types";
import { fetchStyleInsights } from "../api";
import { Sparkles, BarChart2, Heart, Award } from "lucide-react";

interface StyleInsightsProps {
  feedbackRefreshTrigger: number;
}

export const StyleInsights: React.FC<StyleInsightsProps> = ({ feedbackRefreshTrigger }) => {
  const [insights, setInsights] = useState<StyleInsightsData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadInsights() {
      setLoading(true);
      try {
        const data = await fetchStyleInsights();
        setInsights(data);
      } catch (err) {
        console.error("Failed to load insights:", err);
      } finally {
        setLoading(false);
      }
    }
    loadInsights();
  }, [feedbackRefreshTrigger]);

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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
