# CraveAI-style Next.js frontend

Next.js 14 (App Router) + Tailwind UI aligned with **`Design/Zomato_ai_frontend_page_reference.png`** (CraveAI / Stitch reference: hero, red accents, sidebar filters, result cards with “AI insight”).

## Prerequisites

- **Node.js 18+** and npm on your machine.
- **FastAPI** recommender running (default `http://127.0.0.1:8000`).

## CORS (cross-origin dev)

The Next dev server runs on **port 3000** while the API is on **8000**. Set on the API process:

```bash
export RECOMMENDER_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
python3 -m recommender.phase4.main
```

## Setup

```bash
cd frontend
cp .env.example .env.local
# edit .env.local if API is not on 127.0.0.1:8000
npm install
npm run dev
```

Open **http://localhost:3000**.

## API

Uses **`NEXT_PUBLIC_API_BASE_URL`** (see `.env.example`) for:

- `GET /api/v1/localities`
- `GET /health`
- `POST /api/v1/recommend`

## Build

```bash
npm run build && npm start
```
