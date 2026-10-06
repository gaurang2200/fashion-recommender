import React from "react";
import type { WardrobeItem } from "../types";
import { Sparkles } from "lucide-react";
import { getImageUrl } from "../api";

interface WardrobeGridProps {
  items: WardrobeItem[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export const WardrobeGrid: React.FC<WardrobeGridProps> = ({ items, selectedId, onSelect }) => {
  return (
    <div className="w-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-baseline gap-2 mb-6">
        <h2 className="editorial-serif text-lg font-medium text-neutral-800 uppercase tracking-widest">
          My Wardrobe Capsule
        </h2>
        <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold">
          Select a garment to match or scan products matching your whole style profile.
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 md:gap-6">
        {/* Style Profile Pill option */}
        <div
          onClick={() => onSelect("all")}
          className={`editorial-card group flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-all border ${
            selectedId === "all"
              ? "border-neutral-900 bg-neutral-900 text-white"
              : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-950"
          }`}
        >
          <Sparkles className={`w-8 h-8 mb-3 ${selectedId === "all" ? "text-amber-300" : "text-neutral-400 group-hover:text-neutral-900"}`} />
          <h3 className="text-xs uppercase tracking-widest font-semibold mb-1">
            Aggregate Profile
          </h3>
          <p className="text-[10px] opacity-75 font-light leading-relaxed">
            Search using average style profile generated from all wardrobe items.
          </p>
        </div>

        {/* Individual Wardrobe Items */}
        {items.map(item => {
          const isSelected = selectedId === item.id;
          return (
            <div
              key={item.id}
              onClick={() => onSelect(item.id)}
              className={`editorial-card flex flex-col bg-white overflow-hidden cursor-pointer transition-all border ${
                isSelected ? "border-neutral-950 ring-1 ring-neutral-950" : "border-neutral-200"
              }`}
            >
              {/* Image Preview: show extracted transparent crop */}
              <div className="relative aspect-square bg-neutral-50 overflow-hidden border-b border-neutral-100">
                <img
                  src={getImageUrl(item.crop_url)}
                  alt={item.crop_filename}
                  className="w-full h-full object-cover object-center transition-all duration-300 hover:scale-105"
                  onError={(e) => {
                    // Fallback to original image if crop isn't loaded
                    (e.target as HTMLImageElement).src = getImageUrl(item.source_url);
                  }}
                />
                
                {/* Detected category tag */}
                <div className="absolute top-2.5 left-2.5 px-2 py-0.5 bg-white border border-neutral-200 text-[8px] font-bold tracking-wider uppercase text-neutral-600 rounded-sm">
                  {item.category}
                </div>
              </div>

              {/* Color swatches and title */}
              <div className="p-3.5 flex flex-col flex-grow">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-semibold text-neutral-800 uppercase tracking-widest truncate">
                    {item.source_image.replace(/\.[^/.]+$/, "")}
                  </span>
                  
                  {/* Dominant Color swatches */}
                  <div className="flex gap-1">
                    {item.colors.slice(0, 3).map((col, index) => (
                      <div
                        key={index}
                        className="w-2.5 h-2.5 rounded-full border border-neutral-200"
                        style={{ backgroundColor: col }}
                        title={col}
                      />
                    ))}
                  </div>
                </div>

                <div className="flex justify-between items-center mt-auto text-[9px] text-neutral-400 uppercase tracking-widest">
                  <span>Aspect: {item.aspect_ratio}</span>
                  <span>{item.crop_size[0]}×{item.crop_size[1]}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
