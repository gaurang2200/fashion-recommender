import React, { useState, useEffect } from "react";
import type { Product } from "../types";
import { fetchCatalog, triggerScrape } from "../api";
import { Globe, RefreshCcw, CheckCircle2, ShieldAlert } from "lucide-react";

export const CatalogView: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [category, setCategory] = useState("all");
  const [retailer, setRetailer] = useState("all");
  const [total, setTotal] = useState(0);
  const [scraping, setScraping] = useState(false);
  const [scrapeResult, setScrapeResult] = useState<any>(null);

  async function loadCatalog() {
    setLoading(true);
    try {
      const data = await fetchCatalog(category, retailer, 60, 0);
      setProducts(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to load catalog:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCatalog();
  }, [category, retailer]);

  const handleScrape = async () => {
    setScraping(true);
    setScrapeResult(null);
    try {
      const res = await triggerScrape({ category: category === "all" ? "tops" : category, retailer });
      const newAdded = res.new_indexed_count !== undefined ? res.new_indexed_count : res.scraped_count;
      setScrapeResult({
        success: true,
        message: `Successfully completed scraper pass! Scraped ${res.scraped_count} live items (${newAdded} new unique items added & indexed). Total catalog: ${res.total_catalog_size || total} items.`,
        scraped_count: res.scraped_count
      });
      await loadCatalog();
    } catch (err: any) {
      setScrapeResult({
        success: false,
        message: `Scraper error: Rate limit or network block. Check server logs.`
      });
    } finally {
      setScraping(false);
    }
  };

  const getRetailerColor = (ret: string) => {
    switch (ret.toLowerCase()) {
      case "ajio":
        return "bg-slate-900 text-slate-100";
      case "myntra":
        return "bg-rose-50 text-rose-700 border-rose-200";
      case "max fashion":
        return "bg-blue-50 text-blue-700 border-blue-200";
      default:
        return "bg-neutral-100 text-neutral-800";
    }
  };

  return (
    <div className="w-full flex flex-col gap-8">
      {/* Search and Scraper Control Header */}
      <div className="bg-white border border-neutral-200 p-6 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div className="flex flex-col">
          <h2 className="editorial-serif text-lg font-medium text-neutral-800 uppercase tracking-widest">
            Retailer Catalogs Explorer
          </h2>
          <p className="text-xs text-neutral-400 font-light mt-1 max-w-xl">
            Inspect stored items from Ajio, Myntra, and Max Fashion. The scheduled weekly cron keeps this catalog fresh.
          </p>
        </div>

        {/* Manual scraping triggers */}
        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
          <div className="text-xs text-neutral-500 font-medium w-full sm:w-auto">
            Category to Scrape:
          </div>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-transparent border border-neutral-200 px-3 py-1.5 text-xs uppercase tracking-wider outline-none focus:border-neutral-800 flex-grow sm:flex-grow-0"
          >
            <option value="all">All Categories</option>
            <option value="tops">Tops</option>
            <option value="dresses">Dresses</option>
            <option value="bottoms">Bottoms</option>
            <option value="ethnic">Ethnic</option>
            <option value="footwear">Footwear</option>
          </select>

          <select
            value={retailer}
            onChange={(e) => setRetailer(e.target.value)}
            className="bg-transparent border border-neutral-200 px-3 py-1.5 text-xs uppercase tracking-wider outline-none focus:border-neutral-800 flex-grow sm:flex-grow-0"
          >
            <option value="all">All Retailers</option>
            <option value="Ajio">Ajio</option>
            <option value="Myntra">Myntra</option>
            <option value="Max Fashion">Max Fashion</option>
          </select>

          <button
            onClick={handleScrape}
            disabled={scraping}
            className="editorial-button px-5 py-2 flex items-center justify-center gap-2 cursor-pointer font-medium disabled:opacity-55 w-full sm:w-auto"
          >
            <RefreshCcw className={`w-3.5 h-3.5 ${scraping ? "animate-spin" : ""}`} />
            {scraping ? "Scraping Live..." : "Scrape Now"}
          </button>
        </div>
      </div>

      {scrapeResult && (
        <div className={`p-4 border flex items-start gap-3 ${
          scrapeResult.success
            ? "bg-emerald-50 border-emerald-200 text-emerald-800"
            : "bg-red-50 border-red-200 text-red-800"
        }`}>
          {scrapeResult.success ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <p className="text-xs font-semibold">{scrapeResult.success ? "Success" : "Scraper Notice"}</p>
            <p className="text-xs font-light mt-0.5">{scrapeResult.message}</p>
          </div>
        </div>
      )}

      {/* Catalog items display grid */}
      <div>
        <div className="flex justify-between items-baseline mb-6 border-b border-neutral-200 pb-3">
          <h3 className="editorial-serif text-base font-medium text-neutral-800 uppercase tracking-widest">
            Stored Items ({total})
          </h3>
        </div>

        {loading ? (
          <div className="w-full py-20 flex flex-col items-center justify-center text-neutral-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-neutral-800 mb-4"></div>
            <span className="text-xs uppercase tracking-widest font-medium">Loading catalog metadata...</span>
          </div>
        ) : products.length === 0 ? (
          <div className="w-full py-20 bg-white border border-neutral-200 text-center text-neutral-400">
            <Globe className="w-8 h-8 mx-auto mb-3 opacity-60" />
            <p className="text-sm font-medium">No catalog items match these filters.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 md:gap-6">
            {products.map(p => (
              <div key={p.id} className="editorial-card bg-white flex flex-col h-full overflow-hidden border border-neutral-200">
                <div className="relative aspect-[3/4] w-full overflow-hidden bg-neutral-50 border-b border-neutral-100">
                  <img
                    src={p.image_url}
                    alt={p.title}
                    className="h-full w-full object-cover object-top"
                    loading="lazy"
                  />
                  <div className={`absolute bottom-2 left-2 px-1.5 py-0.5 border text-[8px] font-bold tracking-wider uppercase rounded-sm ${getRetailerColor(p.retailer)}`}>
                    {p.retailer}
                  </div>
                </div>
                <div className="p-3 flex flex-col flex-grow">
                  <span className="text-[9px] uppercase tracking-widest text-neutral-400 font-semibold mb-1 truncate">
                    {p.brand}
                  </span>
                  <a
                    href={p.product_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] font-medium text-neutral-800 line-clamp-2 hover:underline mb-2"
                  >
                    {p.title}
                  </a>
                  <div className="mt-auto flex justify-between items-center">
                    <span className="text-xs font-semibold text-neutral-900">₹{p.price}</span>
                    <span className="text-[8px] uppercase tracking-widest font-bold text-rose-500">
                      {p.discount_pct}% OFF
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

