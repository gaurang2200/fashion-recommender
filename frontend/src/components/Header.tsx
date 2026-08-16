import React from "react";
import { RefreshCw } from "lucide-react";

interface HeaderProps {
  wardrobeCount: number;
  catalogCount: number;
  likesCount: number;
  isRescanning: boolean;
  onRescan: () => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  wardrobeCount,
  catalogCount,
  likesCount,
  isRescanning,
  onRescan,
  activeTab,
  setActiveTab
}) => {
  return (
    <header className="sticky top-0 z-40 w-full editorial-glass border-b border-neutral-200">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        {/* Editorial Logo */}
        <div className="flex flex-col">
          <h1 className="editorial-serif text-2xl font-semibold tracking-widest text-neutral-900 uppercase">
            TREND AI
          </h1>
          <span className="text-[10px] tracking-[0.25em] text-neutral-400 uppercase font-light">
            Personal Wardrobe & Recommendation Suite
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex items-center space-x-8">
          <button
            onClick={() => setActiveTab("wardrobe")}
            className={`text-xs uppercase tracking-widest font-medium transition-colors ${
              activeTab === "wardrobe"
                ? "text-neutral-900 border-b border-neutral-900 pb-1"
                : "text-neutral-500 hover:text-neutral-800 pb-1"
            }`}
          >
            My Wardrobe
          </button>
          <button
            onClick={() => setActiveTab("insights")}
            className={`text-xs uppercase tracking-widest font-medium transition-colors ${
              activeTab === "insights"
                ? "text-neutral-900 border-b border-neutral-900 pb-1"
                : "text-neutral-500 hover:text-neutral-800 pb-1"
            }`}
          >
            Aesthetic Insights
          </button>
          <button
            onClick={() => setActiveTab("catalog")}
            className={`text-xs uppercase tracking-widest font-medium transition-colors ${
              activeTab === "catalog"
                ? "text-neutral-900 border-b border-neutral-900 pb-1"
                : "text-neutral-500 hover:text-neutral-800 pb-1"
            }`}
          >
            Catalog Explorer
          </button>
        </nav>

        {/* Interactive Rescan & Stats */}
        <div className="flex items-center space-x-6">
          <div className="hidden lg:flex items-center space-x-4 text-xs text-neutral-500 border-r border-neutral-200 pr-6">
            <div className="flex flex-col items-end">
              <span className="font-semibold text-neutral-800">{wardrobeCount} Items</span>
              <span className="text-[10px]">Wardrobe</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="font-semibold text-neutral-800">{catalogCount} Items</span>
              <span className="text-[10px]">Indexed Catalog</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="font-semibold text-neutral-800 text-rose-600">{likesCount} Likes</span>
              <span className="text-[10px]">Learned Taste</span>
            </div>
          </div>

          <button
            onClick={onRescan}
            disabled={isRescanning}
            className="editorial-button px-5 py-2.5 flex items-center gap-2 cursor-pointer font-medium disabled:opacity-55"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRescanning ? "animate-spin" : ""}`} />
            {isRescanning ? "Scanning Folders..." : "Scan Wardrobe"}
          </button>
        </div>
      </div>
    </header>
  );
};
