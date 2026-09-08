import { useState, useEffect } from "react";
import { Header } from "./components/Header";
import { WardrobeGrid } from "./components/WardrobeGrid";
import { RecommendView } from "./components/RecommendView";
import { CatalogView } from "./components/CatalogView";
import { StyleInsights } from "./components/StyleInsights";
import { fetchHealth, fetchWardrobe, rescanWardrobe, submitFeedback, fetchCatalogStatus } from "./api";
import type { WardrobeItem, Product } from "./types";
import { CheckCircle2, ShieldAlert } from "lucide-react";

function App() {
  const [activeTab, setActiveTab] = useState<string>("wardrobe");
  const [wardrobeItems, setWardrobeItems] = useState<WardrobeItem[]>([]);
  const [selectedGarment, setSelectedGarment] = useState<WardrobeItem | null>(null);
  const [stats, setStats] = useState({
    catalogCount: 0,
    likesCount: 0
  });

  const [rescanning, setRescanning] = useState<boolean>(false);
  const [feedbackTrigger, setFeedbackTrigger] = useState<number>(0);
  const [notice, setNotice] = useState<{ success: boolean; text: string } | null>(null);

  // Load wardrobe & health stats
  const loadData = async () => {
    try {
      const wardrobe = await fetchWardrobe();
      setWardrobeItems(wardrobe.items);
      
      const health = await fetchHealth();
      setStats({
        catalogCount: health.catalog_count,
        likesCount: health.likes_count
      });
    } catch (err) {
      console.error("Failed to fetch initial wardrobe data:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRescan = async () => {
    setRescanning(true);
    setNotice(null);
    try {
      const res = await rescanWardrobe(false);
      const newCount = res.new_items_count || 0;
      if (newCount > 0) {
        setNotice({
          success: true,
          text: `Wardrobe scanned! Discovered ${newCount} new garment${newCount > 1 ? "s" : ""}. Finding matching pieces online in the background...`
        });
        
        // Poll status in background and auto-refresh recommendations when done
        const pollInterval = setInterval(async () => {
          try {
            const status = await fetchCatalogStatus();
            if (!status.is_indexing) {
              clearInterval(pollInterval);
              await loadData();
              setFeedbackTrigger(prev => prev + 1);
              setNotice({
                success: true,
                text: `Catalog enriched with new matching pieces! Total items: ${status.total_products}`
              });
            }
          } catch (e) {
            clearInterval(pollInterval);
          }
        }, 3000);
      } else {
        setNotice({
          success: true,
          text: `Wardrobe scanned successfully! All ${res.data.total_garments} garments are up to date.`
        });
      }
      await loadData();
    } catch (err) {
      setNotice({
        success: false,
        text: "Scanning failed. Check server backend connection."
      });
    } finally {
      setRescanning(false);
    }
  };

  const handleFeedback = async (productId: string, isLike: boolean, productData?: Product) => {
    try {
      await submitFeedback(productId, isLike, productData);
      // Reload stats and trigger recomposition
      const health = await fetchHealth();
      setStats(prev => ({ ...prev, likesCount: health.likes_count }));
      setFeedbackTrigger(prev => prev + 1);
    } catch (err) {
      console.error("Feedback submission error:", err);
    }
  };

  const handleSelectGarment = (id: string) => {
    if (id === "all") {
      setSelectedGarment(null);
    } else {
      const item = wardrobeItems.find(x => x.id === id);
      if (item) {
        setSelectedGarment(item);
      }
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#fafafa]">
      {/* Header masthead */}
      <Header
        wardrobeCount={wardrobeItems.length}
        catalogCount={stats.catalogCount}
        likesCount={stats.likesCount}
        isRescanning={rescanning}
        onRescan={handleRescan}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Container */}
      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 w-full flex flex-col gap-8 sm:gap-10">
        {/* Notice alert */}
        {notice && (
          <div className={`p-4 border flex items-center gap-3 transition-all ${
            notice.success
              ? "bg-emerald-50 border-emerald-100 text-emerald-800"
              : "bg-red-50 border-red-100 text-red-800"
          }`}>
            {notice.success ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-red-600" />
            )}
            <span className="text-xs font-medium">{notice.text}</span>
          </div>
        )}

        {/* Tab Router views */}
        {activeTab === "wardrobe" && (
          <div className="flex flex-col gap-10">
            {/* Wardrobe selection Drawer */}
            <section className="bg-white border border-neutral-200 p-6">
              <WardrobeGrid
                items={wardrobeItems}
                selectedId={selectedGarment ? selectedGarment.id : "all"}
                onSelect={handleSelectGarment}
              />
            </section>

            {/* Recommendation Feed drawer */}
            <section className="w-full">
              <RecommendView
                selectedGarment={selectedGarment}
                onFeedback={handleFeedback}
                feedbackRefreshTrigger={feedbackTrigger}
              />
            </section>
          </div>
        )}

        {activeTab === "insights" && (
          <section className="w-full">
            <StyleInsights feedbackRefreshTrigger={feedbackTrigger} />
          </section>
        )}

        {activeTab === "catalog" && (
          <section className="w-full">
            <CatalogView />
          </section>
        )}
      </main>

      {/* Footer copyright */}
      <footer className="border-t border-neutral-200 bg-white py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row justify-between items-center gap-2 text-[10px] uppercase tracking-widest text-neutral-400 font-medium text-center sm:text-left">
          <span>Trend AI Style Matching Engine v2</span>
          <span>© 2026 Gaurang. All Rights Reserved.</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
