# Fashion-2 AI Stylist - Cloud Deployment Guide

This guide walks you through deploying your **Fashion-2 AI Stylist & Recommendation Engine** online on [Render](https://render.com) (or Vercel + Render) with your exact pre-loaded database, vector index, wardrobe photos, and catalog items.

---

## 🏗️ Architecture Overview

- **Backend Web Service (FastAPI + Docker)**:
  - Runs inside Python 3.10 Docker container.
  - Pre-seeded with your current `data/products.json`, `data/catalog.index`, `data/wardrobe.json`, `data/feedback.json`, `clothes/`, and `crops/`.
  - Uses PyTorch CPU and HuggingFace Transformers for 512-dim Fashion-CLIP vector embeddings and FAISS nearest-neighbor search.
- **Frontend Web App (React + Vite)**:
  - Deployed as a high-performance Static Site.
  - Automatically configured to connect to your deployed online backend URL.

---

## 🚀 Quick Option 1: Deploy with Render Blueprint (Recommended - 1 Click)

Render reads the `render.yaml` blueprint included in this repository to automatically configure both backend and frontend services.

### Step 1: Push Code to GitHub
1. Make sure your latest changes and data are committed to Git:
   ```bash
   git add .
   git commit -m "Prepare Fashion-2 for online cloud deployment"
   git push origin main
   ```

### Step 2: Deploy on Render
1. Sign in to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** in the top right and select **Blueprint**.
3. Connect your GitHub repository containing this codebase.
4. Render will automatically detect `render.yaml` and create two services:
   - **`fashion-2-backend`** (Docker Web Service)
   - **`fashion-2-frontend`** (Static Site with `VITE_API_URL` environment variable automatically linked)
5. Click **Apply**. Render will build the Docker container and deploy both services!

---

## 🛠️ Option 2: Manual Setup on Render

If you prefer setting up services manually on Render:

### A. Deploy Backend Web Service
1. On Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Choose **Docker** as the Runtime.
4. Set **Port**: `8000`.
5. Set **Health Check Path**: `/api/health`.
6. Click **Create Web Service**.
7. Copy your backend service URL (e.g., `https://fashion-2-backend.onrender.com`).

### B. Deploy Frontend Static Site
1. Click **New +** → **Static Site**.
2. Connect the same repository.
3. Set **Build Command**: `cd frontend && npm install && npm run build`
4. Set **Publish Directory**: `./frontend/dist`
5. Add Environment Variable:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://fashion-2-backend.onrender.com/api` (use your actual backend URL from step A)
6. Click **Create Static Site**.

---

## ⚡ Option 3: Separate Frontend on Vercel + Backend on Render

If you prefer Vercel for the React frontend:

1. Deploy the Backend on Render as described in Option 2A.
2. Go to [Vercel Dashboard](https://vercel.com) → **Add New** → **Project**.
3. Import your GitHub repository.
4. Set **Root Directory**: `frontend`.
5. Add Environment Variable:
   - `VITE_API_URL`: `https://your-render-backend-url.onrender.com/api`
6. Click **Deploy**.

---

## 🧪 Verifying Your Deployed Website

Once deployed:

1. **Check Backend Health**:
   Visit `https://your-backend-url.onrender.com/api/health`
   You should see:
   ```json
   {
     "status": "healthy",
     "service": "Fashion-2 Engine",
     "wardrobe_count": 22,
     "catalog_count": 558,
     "index_ready": true
   }
   ```

2. **Open Frontend Web App**:
   Visit your static site URL. You will see:
   - Your full capsule wardrobe loaded with crop previews.
   - Live AI recommendations powered by FAISS and CLIP.
   - Interactive active preference learning (thumbs up / down).
   - Style Insights analytics dashboard.

---

## 💾 Persistent Storage Note

The pre-packaged database (`products.json`, `catalog.index`, `wardrobe.json`, `feedback.json`, `clothes/`, `crops/`) is included inside the Docker container.
- If you mount a Render Persistent Disk at `/app/data`, any new likes/dislikes or live scraped catalog items will persist across deployments.
