# TradeSentient 📈
> Real-time market intelligence dashboard for Crypto, US Stocks, and Indian Stocks.

TradeSentient provides a unified view of the top 50 assets across global markets, normalized to INR, with real-time price updates, sentiment analysis, and technical trading signals.

## 🌐 Live Demo
- **Frontend**: [https://tradesentient.netlify.app](https://tradesentient.netlify.app)
- **Backend API**: [https://tradesentient-1.onrender.com](https://tradesentient-1.onrender.com)
- **API Docs**: [https://tradesentient-1.onrender.com/docs](https://tradesentient-1.onrender.com/docs)
- **Security**: See [SECURITY.md](SECURITY.md) for security features (9/10 rating)

## ✨ Features
- **Dynamic Asset Discovery**: Automatically fetches Top 50 Crypto (CoinGecko), S&P 500 (Wikipedia), and NIFTY 50 (NSE).
- **Real-time Data**: WebSocket streaming for sub-second price updates.
- **INR Normalization**: All prices converted to Indian Rupee (₹) using live forex rates.
- **Sentiment Analysis**: Aggregates news/social sentiment (simulated/feed).
- **Technical Signals**: Moving Average Crossovers (SMA) alerts.
- **Robust Architecture**: SQLite (WAL mode) + Redis Caching + Celery Workers.
- **Polished UI**: Dark mode, glassmorphism, and smooth WebM animations.

## 🛠 Tech Stack
- **Frontend**: React (Vite), Recharts, Lucide Icons, WebM Animations.
- **Backend**: Python (FastAPI), SQLAlchemy (Async), WebSockets.
- **Data Engine**: Celery + Redis (Background Ingestion).
- **Database**: SQLite (Dev) / PostgreSQL (Prod).

## 🚀 Quick Start
### Prerequisites
- Python 3.10+
- Node.js 18+
- Redis Server (running on localhost:6379)

### 1. Backend Setup
```bash
# Create virtual env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (if not running)
redis-server

# Run Backend
uvicorn backend.main:app --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Access the app at `http://localhost:5173`.

### 3. Start Data Ingestion
To populate the database with real-time data:
```bash
# Terminal 3
python -m worker.ingest_script
```

## 📦 Deployment
The project is deployed on:
- **Frontend**: **Netlify** - [https://tradesentient.netlify.app](https://tradesentient.netlify.app)
- **Backend**: **Render** - [https://tradesentient-1.onrender.com](https://tradesentient-1.onrender.com)

### Security Features
- ✅ Rate limiting (100 req/min public, 1000 req/min worker)
- ✅ Input validation & XSS prevention
- ✅ CORS hardening
- ✅ OWASP security headers
- ✅ Request size limits

See [SECURITY.md](SECURITY.md) for complete security documentation.

## 🎨 Theme
- **Background**: `#c2dbe7` (Pastel Blue)
- **Cards**: `#fff0b5` (Cream)
- **Text**: `#432e2e` (Dark Brown)

## 📁 Project Structure
```
TradeSentient/
├── backend/            # FastAPI app & logic
│   ├── main.py         # Entry point & WebSockets
│   ├── ticker_config.py # Dynamic asset fetching
│   └── ...
├── frontend/           # React App
│   ├── public/animations # Local WebM assets
│   ├── src/components  # UI Components
│   └── ...
├── worker/             # Celery tasks & Ingest scripts
└── requirements.txt    # Python dependencies
```

## 📄 License
MIT
