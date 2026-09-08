import React from "react";
import type { FilterOptions } from "../types";
import { Sliders } from "lucide-react";

interface FilterBarProps {
  filters: FilterOptions;
  setFilters: React.Dispatch<React.SetStateAction<FilterOptions>>;
  categories: string[];
  retailers: string[];
  sizes: string[];
  priceBounds: { min: number; max: number };
  sortOptions: Array<{ id: string; label: string }>;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  setFilters,
  categories,
  retailers,
  sizes,
  priceBounds,
  sortOptions
}) => {
  const handleCategoryChange = (cat: string) => {
    setFilters(prev => ({ ...prev, category: cat }));
  };

  const handleRetailerChange = (ret: string) => {
    setFilters(prev => ({ ...prev, retailer: ret }));
  };

  const handleSizeChange = (sz: string) => {
    setFilters(prev => ({ ...prev, size: sz }));
  };

  const handlePriceChange = (e: React.ChangeEvent<HTMLInputElement>, type: "min" | "max") => {
    const val = e.target.value === "" ? null : Number(e.target.value);
    setFilters(prev => ({
      ...prev,
      [type === "min" ? "min_price" : "max_price"]: val
    }));
  };

  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilters(prev => ({ ...prev, sort_by: e.target.value }));
  };

  const handleWeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters(prev => ({ ...prev, preference_weight: Number(e.target.value) / 100 }));
  };

  return (
    <div className="w-full bg-white border border-neutral-200 p-6 flex flex-col gap-6">
      {/* Category Selection Tabs */}
      <div>
        <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold block mb-3">
          Category
        </span>
        <div className="flex flex-wrap gap-2">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => handleCategoryChange(cat)}
              className={`px-4 py-2 border text-xs uppercase tracking-wider font-medium cursor-pointer transition-all ${
                filters.category === cat
                  ? "pill-active"
                  : "pill-inactive hover:border-neutral-400"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Retailer Selector */}
        <div>
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold block mb-3">
            Retailer
          </span>
          <div className="flex flex-wrap gap-2">
            {retailers.map(ret => (
              <button
                key={ret}
                onClick={() => handleRetailerChange(ret)}
                className={`px-4 py-2 border text-xs uppercase tracking-wider font-medium cursor-pointer transition-all ${
                  filters.retailer === ret
                    ? "pill-active"
                    : "pill-inactive hover:border-neutral-400"
                }`}
              >
                {ret === "all" ? "All Retailers" : ret}
              </button>
            ))}
          </div>
        </div>

        {/* Size Selector */}
        <div>
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold block mb-3">
            Size Availability
          </span>
          <div className="relative">
            <select
              value={filters.size}
              onChange={(e) => handleSizeChange(e.target.value)}
              className="w-full bg-transparent border border-neutral-200 px-3 py-2 text-xs uppercase tracking-wider font-medium text-neutral-700 outline-none focus:border-neutral-800"
            >
              {sizes.map(sz => (
                <option key={sz} value={sz}>
                  {sz === "all" ? "All Sizes" : `Size ${sz}`}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Sorting Selection */}
        <div>
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold block mb-3">
            Sort By
          </span>
          <div className="relative">
            <select
              value={filters.sort_by}
              onChange={handleSortChange}
              className="w-full bg-transparent border border-neutral-200 px-3 py-2 text-xs uppercase tracking-wider font-medium text-neutral-700 outline-none focus:border-neutral-800"
            >
              {sortOptions.map(opt => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <hr className="border-neutral-100" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8 items-center">
        {/* Price Ranges */}
        <div>
          <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold block mb-3">
            Price Range (INR ₹)
          </span>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4">
            <input
              type="number"
              placeholder={`Min: ₹${priceBounds.min}`}
              value={filters.min_price === null ? "" : filters.min_price}
              onChange={(e) => handlePriceChange(e, "min")}
              className="w-full border border-neutral-200 px-3 py-2 text-xs tracking-wider outline-none focus:border-neutral-800"
            />
            <span className="text-neutral-400 text-xs text-center hidden sm:inline">—</span>
            <input
              type="number"
              placeholder={`Max: ₹${priceBounds.max}`}
              value={filters.max_price === null ? "" : filters.max_price}
              onChange={(e) => handlePriceChange(e, "max")}
              className="w-full border border-neutral-200 px-3 py-2 text-xs tracking-wider outline-none focus:border-neutral-800"
            />
          </div>
        </div>

        {/* Personalized Taste Slider */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-[10px] uppercase tracking-widest text-neutral-400 font-semibold flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5" />
               Taste Customization Weight
            </span>
            <span className="text-xs font-semibold text-neutral-700">
              {Math.round(filters.preference_weight * 100)}% Personalization
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={Math.round(filters.preference_weight * 100)}
            onChange={handleWeightChange}
            className="w-full accent-neutral-900 cursor-pointer"
          />
          <span className="text-[9px] text-neutral-400 mt-1 block font-light leading-normal">
            Low weight = pure visual matching. High weight = heavily shifts recommendation order to match products you marked thumbs-up.
          </span>
        </div>
      </div>
    </div>
  );
};
