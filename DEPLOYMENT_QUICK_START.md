# 🚀 Quick Deployment Commands

## Prerequisites Checklist
- [ ] Code committed to GitHub
- [ ] GitHub repository: `Sly-kitsune/TradeSentient`
- [ ] Render account created
- [ ] Netlify account created

---

## Step 1: Deploy Backend to Render

### Via Render Dashboard
1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect repository: `Sly-kitsune/TradeSentient`
4. Render auto-detects `render.yaml` ✅
5. Click **"Create Web Service"**
6. Wait 3-5 minutes
7. **Copy your backend URL**: `https://tradesentient-backend.onrender.com`

---

## Step 2: Deploy Frontend to Netlify

### Via Netlify Dashboard
1. Go to https://app.netlify.com/
2. Click **"Add new site"** → **"Import an existing project"**
3. Choose **GitHub** → Select `Sly-kitsune/TradeSentient`
4. Configure:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
5. **Add environment variable**:
   - Go to **Site settings** → **Environment variables**
   - Key: `VITE_API_URL`
   - Value: `https://tradesentient-backend.onrender.com` (your Render URL)
6. Click **"Deploy site"**
7. Wait 2-3 minutes

---

## Step 3: Verify Deployment

### Test Backend
```bash
# Should return API info
curl https://tradesentient-backend.onrender.com/

# Should return tickers
curl https://tradesentient-backend.onrender.com/tickers
```

### Test Frontend
1. Open Netlify URL in browser
2. Press F12 → Console tab
3. Check for errors (should be none)
4. Verify market data loads

---

## 📝 Important Notes

- **Backend URL**: Save it! You need it for Netlify environment variables
- **Free tier**: Render may sleep after 15 min inactivity (first request takes ~30s to wake)
- **CORS**: Already configured to allow all origins
- **WebSockets**: Supported on both platforms

---

## 🔗 Quick Links

| Service | URL |
|---------|-----|
| Render Dashboard | https://dashboard.render.com/ |
| Netlify Dashboard | https://app.netlify.com/ |
| Deployment Guide | See `netlify_deployment_guide.md` |

---

## ⚡ One-Line Test Commands

After deployment, test with:

```bash
# Test backend
curl https://YOUR-BACKEND.onrender.com/

# Test frontend (in browser)
# Just open: https://YOUR-SITE.netlify.app
```

Replace `YOUR-BACKEND` and `YOUR-SITE` with your actual URLs!
