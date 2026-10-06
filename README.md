# 👗 Fashion Recommender & AI Stylist

A multimodal AI wardrobe curation and fashion recommendation engine powered by **Fashion-CLIP**, **FAISS vector search**, and a modern **React + Vite** frontend.

---

## 🌟 Highlights

- **Capsule Wardrobe Ingestion**: Automatic garment segmentation, cropping, and 512-dimensional vector embedding.
- **Multimodal AI Recommendations**: Fashion-CLIP cosine similarity search matched against live e-commerce catalogs (Myntra, Ajio, Max Fashion).
- **Interactive Feedback Engine**: Real-time preference learning with liked/disliked catalog updates and personalized style insights.
- **Responsive UI**: Built with React, Tailwind CSS, Lucide icons, and modern animations.

---

## 🏗️ Architecture

```
fashion-recommender/
├── backend/            # FastAPI + PyTorch + FAISS + Fashion-CLIP
├── frontend/           # React + TypeScript + Vite + Tailwind CSS
├── clothes/            # Pre-loaded wardrobe source photos
├── crops/              # Segmented garment crops
├── data/               # Vector index, product catalog, wardrobe & feedback JSON
├── Dockerfile          # Production container setup for backend
├── render.yaml         # One-click Render deployment blueprint
└── DEPLOYMENT.md       # Detailed cloud hosting guide
```

---

## 🚀 Hosting & Deployment

### 1. Frontend on Vercel (Recommended)
1. Go to [Vercel Dashboard](https://vercel.com/new).
2. Select your repository: `gaurang2200/fashion-recommender`.
3. Configure settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Set Environment Variable:
   - `VITE_API_URL`: Your hosted backend URL (e.g. `https://your-backend.onrender.com/api`)
5. Click **Deploy**!

### 2. Backend on Render / Cloud Container
- Use the included [Dockerfile](Dockerfile) or [render.yaml](render.yaml).
- Runtime: **Docker**
- Port: `8000`
- Health check: `/api/health`

For step-by-step instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 💻 Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.
