import React, { useState } from "react";
import { RefreshCw, Menu, X } from "lucide-react";

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleTabClick = (tab: string) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 w-full editorial-glass border-b border-neutral-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-20 flex items-center justify-between">
        {/* Editorial Logo */}
        <div className="flex flex-col">
          <h1 className="editorial-serif text-xl sm:text-2xl font-semibold tracking-widest text-neutral-900 uppercase">
            TREND AI
          </h1>
          <span className="text-[9px] sm:text-[10px] tracking-[0.2em] sm:tracking-[0.25em] text-neutral-400 uppercase font-light">
            Personal Wardrobe & Recommendation Suite
          </span>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-6 lg:space-x-8">
          <button
            onClick={() => handleTabClick("wardrobe")}
            className={`text-xs uppercase tracking-widest font-medium transition-colors cursor-pointer ${
              activeTab === "wardrobe"
                ? "text-neutral-900 border-b border-neutral-900 pb-1"
                : "text-neutral-500 hover:text-neutral-800 pb-1"
            }`}
          >
            My Wardrobe
          </button>
          <button
            onClick={() => handleTabClick("insights")}
            className={`text-xs uppercase tracking-widest font-medium transition-colors cursor-pointer ${
              activeTab === "insights"
                ? "text-neutral-900 border-b border-neutral-900 pb-1"
                : "text-neutral-500 hover:text-neutral-800 pb-1"
            }`}
          >
            Aesthetic Insights
          </button>
          <button
            onClick={() => handleTabClick("catalog")}
            className={`text-xs uppercase tracking-widest font-medium transition-colors cursor-pointer ${
              activeTab === "catalog"
                ? "text-neutral-900 border-b border-neutral-900 pb-1"
                : "text-neutral-500 hover:text-neutral-800 pb-1"
            }`}
          >
            Catalog Explorer
          </button>
        </nav>

        {/* Desktop Rescan & Stats */}
        <div className="hidden md:flex items-center space-x-6">
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
            className="editorial-button px-4 lg:px-5 py-2.5 flex items-center gap-2 cursor-pointer font-medium disabled:opacity-55"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRescanning ? "animate-spin" : ""}`} />
            {isRescanning ? "Scanning..." : "Scan Wardrobe"}
          </button>
        </div>

        {/* Mobile Hamburger Toggle */}
        <div className="flex items-center gap-3 md:hidden">
          <button
            onClick={onRescan}
            disabled={isRescanning}
            className="editorial-button p-2 flex items-center justify-center cursor-pointer disabled:opacity-55"
            title="Scan Wardrobe"
          >
            <RefreshCw className={`w-4 h-4 ${isRescanning ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 text-neutral-700 hover:text-neutral-900 border border-neutral-200 rounded-sm bg-white"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-neutral-200 bg-white px-6 py-5 flex flex-col gap-5 shadow-lg animate-in slide-in-from-top-2 duration-200">
          <nav className="flex flex-col gap-3">
            <button
              onClick={() => handleTabClick("wardrobe")}
              className={`text-left text-xs uppercase tracking-widest font-semibold py-2 border-b ${
                activeTab === "wardrobe"
                  ? "text-neutral-900 border-neutral-900"
                  : "text-neutral-500 border-neutral-100"
              }`}
            >
              My Wardrobe
            </button>
            <button
              onClick={() => handleTabClick("insights")}
              className={`text-left text-xs uppercase tracking-widest font-semibold py-2 border-b ${
                activeTab === "insights"
                  ? "text-neutral-900 border-neutral-900"
                  : "text-neutral-500 border-neutral-100"
              }`}
            >
              Aesthetic Insights
            </button>
            <button
              onClick={() => handleTabClick("catalog")}
              className={`text-left text-xs uppercase tracking-widest font-semibold py-2 border-b ${
                activeTab === "catalog"
                  ? "text-neutral-900 border-neutral-900"
                  : "text-neutral-500 border-neutral-100"
              }`}
            >
              Catalog Explorer
            </button>
          </nav>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-neutral-100 text-center">
            <div className="bg-neutral-50 p-2.5 border border-neutral-100">
              <span className="block font-semibold text-neutral-800 text-sm">{wardrobeCount}</span>
              <span className="text-[9px] uppercase tracking-wider text-neutral-400">Wardrobe</span>
            </div>
            <div className="bg-neutral-50 p-2.5 border border-neutral-100">
              <span className="block font-semibold text-neutral-800 text-sm">{catalogCount}</span>
              <span className="text-[9px] uppercase tracking-wider text-neutral-400">Catalog</span>
            </div>
            <div className="bg-neutral-50 p-2.5 border border-neutral-100">
              <span className="block font-semibold text-rose-600 text-sm">{likesCount}</span>
              <span className="text-[9px] uppercase tracking-wider text-neutral-400">Likes</span>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

