# 🚀 3-Minute Railway Deployment Guide

This guide walks you through deploying the **MahaSetu RPA Ecosystem** to [Railway.app](https://railway.app) with full Playwright browser automation and persistent storage.

---

## Why Railway is 100% Ready

The repository contains all native configuration files required by Railway:
- [`railway.json`](railway.json): Directs Railway to use the production [`Dockerfile`](Dockerfile) and configures the `/api/health` healthcheck.
- [`Dockerfile`](Dockerfile): Based on Microsoft's official `mcr.microsoft.com/playwright/python:v1.40.0-jammy` with all Chromium Linux binaries and shared libraries pre-installed.
- Dynamic `$PORT` handling: Server automatically binds to `0.0.0.0:$PORT` provided dynamically by Railway.
- Extension packaging: Automatically builds and exposes the extension zip package for users to download directly from your live Railway instance at `/api/extension/download`.

---

## Step-by-Step Deployment to Railway

### Step 1: Push Code to GitHub
Ensure all your files are committed and pushed to your GitHub repository:
```bash
git add .
git commit -m "Deploy MahaSetu RPA Ecosystem to Railway"
git push origin <your-branch>
```

---

### Step 2: Create Project on Railway
1. Go to [railway.com](https://railway.com/) and log in with GitHub.
2. Click **+ New Project**.
3. Select **Deploy from GitHub repo**.
4. Choose your `sih-knodeknights` (or `RPA-Bots`) repository.
5. Railway will automatically detect [`railway.json`](railway.json) and start building via the `Dockerfile`.

---

### Step 3: Add a Persistent Volume (Crucial for Bot Workflows)
To ensure your created bots, path traces, and recordings persist when Railway redeploys:
1. In your Railway Project dashboard, click on your service.
2. Navigate to the **Settings** tab.
3. Scroll down to the **Volumes** section and click **+ Add Volume**.
4. Set the **Mount Path** to:
   ```text
   /app/backend/data
   ```
5. Click **Add Volume**.

---

### Step 4: Configure Environment Variables (Optional)
In your service's **Variables** tab in Railway, you can customize:

| Variable | Recommended Value | Note |
| :--- | :--- | :--- |
| `PORT` | *(Leave empty)* | Railway injects this automatically |
| `FLASK_ENV` | `production` | Enables production optimizations |
| `CORS_ORIGINS` | `*` | Allows Chrome Extension access from any tab |
| `PLAYWRIGHT_HEADLESS_DEFAULT` | `true` | Runs bots headlessly on cloud servers |
| `SECRET_KEY` | *(Click "Add Secret")* | Generates a random secure key |

---

### Step 5: Generate a Public Domain
1. In your service's **Settings** tab, scroll to **Networking**.
2. Under **Public Networking**, click **Generate Domain**.
3. Railway will give you a live URL, such as:
   ```text
   https://mahasetu-rpa-production.up.railway.app
   ```
4. Click your generated URL to open the MahaSetu Visual Flowchart Builder live!

---

## Step 6: Connect the Chrome Extension to Your Railway Instance

Once your Railway instance is live:
1. Open Google Chrome with the MahaSetu RPA Recorder extension installed.
2. Click the extension icon in the toolbar.
3. Click the gear icon (`⚙`) in the header (or right-click -> **Options**).
4. Enter your Railway domain:
   ```text
   https://your-service-name.up.railway.app
   ```
5. Click **Test Ping** — the indicator turns green: `✓ Connected (v1.0.0)`.
6. Click **Save Settings**.
7. Any workflow you now record on any tab will automatically export directly to your live Railway instance!

---

## Step 7: Verify Railway Deployment

Run the automated verification suite from your terminal against your live Railway URL:
```bash
python verify_deployment.py --url https://your-service-name.up.railway.app
```

This verifies:
- `/api/health` healthcheck probe
- Security headers
- Visual builder, extension setup guide, and demo target
- Pre-packaged extension zip download
- Bot Catalog & payload generators
- Extension recording ingestion endpoint
- Headless Playwright browser automation execution
