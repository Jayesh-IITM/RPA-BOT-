# MahaSetu RPA Ecosystem - Production Deployment Guide

This guide provides step-by-step instructions for deploying the **MahaSetu RPA Ecosystem** to production across both the **Chrome Extension** and the **Web Dev / Backend Infrastructure**.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              CHROME EXTENSION (Manifest V3)             │
│  - In-page recorder (clicks, inputs, canvas gestures)   │
│  - Resilient selector engine (ID, CSS, XPath, Text)     │
│  - Configurable server URL (storage.sync / Options UI)  │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTPS / REST JSON
                            ▼
┌─────────────────────────────────────────────────────────┐
│            MAHASETU WEB & API BACKEND (WSGI)            │
│  - Production WSGI: Waitress (Windows) / Gunicorn (Linux│
│  - Visual Flowchart Builder Canvas (/builder)           │
│  - REST & XML Execution Endpoints (/api/bots/<id>/exec) │
│  - Real-time SSE Live Execution Streaming (/test-stream)│
│  - Health Check & Monitoring API (/api/health)          │
│  - Direct Extension ZIP Distribution (/api/ext/download)│
└───────────────────────────┬─────────────────────────────┘
                            │ Headed (Live UI) / Headless
                            ▼
┌─────────────────────────────────────────────────────────┐
│          PLAYWRIGHT BROWSER AUTOMATION ENGINE           │
│  - Multi-selector fallback resolution                   │
│  - Display-less cloud fallback detection                │
│  - Live step screenshot capture & base64 streaming     │
│  - Branch condition evaluation (Success vs Failure)     │
└─────────────────────────────────────────────────────────┘
```

---

## Part 1: Web Dev / Backend Deployment

### Option A: 1-Command Docker Deployment (Recommended for Cloud)

The backend includes a production-ready `Dockerfile` based on Microsoft's official Playwright Python image (`mcr.microsoft.com/playwright/python:v1.40.0-jammy`), ensuring all Linux OS browser dependencies and Chromium binaries are pre-installed.

1. **Start with Docker Compose**:
   ```bash
   docker compose up --build -d
   ```
2. **Verify Container Health**:
   ```bash
   docker ps
   curl -f http://localhost:5000/api/health
   ```
3. **Data Persistence**:
   Saved bots, recordings, and screenshots are automatically persisted in `./backend/data` via volume mapping.

---

### Option B: Cloud PaaS Deployment

#### 1. Render.com
- A pre-configured [`render.yaml`](file:///c:/RPA%20Bots/render.yaml) blueprint is included in the root directory.
- Connect your Git repository to Render.
- Render will automatically detect `render.yaml`, build the Docker container, mount a 5GB persistent disk for `/app/backend/data`, and configure health checks on `/api/health`.

#### 2. Railway / Fly.io / Heroku
- A [`Procfile`](file:///c:/RPA%20Bots/Procfile) is provided:
  ```procfile
  web: gunicorn --workers=2 --threads=4 --bind=0.0.0.0:$PORT --timeout=120 wsgi:application
  ```
- Deploy directly with `railway up` or `fly deploy`.

---

### Option C: Bare-Metal Linux Server (Systemd + Gunicorn + Nginx)

1. **Install System Dependencies & Playwright**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-venv git
   git clone <your-repo-url> /var/www/mahasetu
   cd /var/www/mahasetu
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt gunicorn
   playwright install --with-deps chromium
   python scripts/package_extension.py
   ```

2. **Create Systemd Service (`/etc/systemd/system/mahasetu.service`)**:
   ```ini
   [Unit]
   Description=MahaSetu RPA Backend Service
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/mahasetu
   Environment="PATH=/var/www/mahasetu/venv/bin"
   EnvironmentFile=/var/www/mahasetu/.env
   ExecStart=/var/www/mahasetu/venv/bin/gunicorn --workers 2 --threads 4 --bind 127.0.0.1:5000 --timeout 120 wsgi:application
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now mahasetu
   ```

3. **Configure Nginx Reverse Proxy**:
   Use the provided template [`nginx.conf.example`](file:///c:/RPA%20Bots/nginx.conf.example).
   > [!IMPORTANT]
   > Ensure `proxy_buffering off;` is configured for `/api/bots/` so Server-Sent Events (SSE) stream step-by-step logs and screenshots in real-time.

---

### Option D: Windows Server Deployment (Waitress)

On Windows Server, use the pure-Python multi-threaded `waitress` server:
```powershell
python start_production.py
```
To run as a Windows Service automatically on system boot:
1. Download [NSSM (Non-Sucking Service Manager)](https://nssm.cc/).
2. Run:
   ```powershell
   nssm install MahaSetuRPA "C:\Path\To\Python\python.exe" "C:\RPA Bots\start_production.py"
   nssm start MahaSetuRPA
   ```

---

## Part 2: Chrome Extension Deployment

### 1. Automated Packaging
Build a verified, production-ready `.zip` package with one command:
```bash
python scripts/package_extension.py
```
This script:
- Validates [`manifest.json`](file:///c:/RPA%20Bots/extension/manifest.json) syntax and permissions.
- Validates the presence of all icons (`16x16`, `32x32`, `48x48`, `128x128`), popup files, options files, and background workers.
- Generates `dist/mahasetu-rpa-recorder-v1.0.0.zip`.
- Automatically copies the archive to `backend/static/downloads/` for in-portal user downloads.

---

### 2. Chrome Web Store Publishing Guide

To publish on the official [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole/):

1. **Sign in to Developer Console**:
   - Access the Chrome Web Store Developer Console with your Google account.
   - Pay the one-time $5 developer registration fee if not already activated.
2. **Upload Package**:
   - Click **Add new item**.
   - Upload the generated zip bundle: `dist/mahasetu-rpa-recorder-v1.0.0.zip`.
3. **Store Listing Details**:
   - **Name**: `MahaSetu RPA Recorder`
   - **Summary**: `Intelligent user action recorder with resilient multi-selectors and direct export to MahaSetu RPA visual workflow builder.`
   - **Category**: `Productivity / Developer Tools`
   - **Icons**: Icons are pre-bundled in the ZIP (`128x128` used by store).
   - **Screenshots**: Upload 1280x800 screenshots of the recording floating bar and visual builder.
4. **Privacy & Permissions Justification**:
   - **storage**: Used to store recording traces and user's configured backend server URL.
   - **activeTab & scripting**: Used to inject recorder control bar on the tab the user explicitly chooses to automate.
   - **host_permissions (`<all_urls>`)**: Required to allow citizens/developers to record workflows on government and enterprise web portals.
5. **Publish**: Click **Submit for Review**. Google usually approves within 24-48 hours.

---

### 3. Enterprise / Organization Internal Deployment

If deploying internally across corporate or government workstations without the public Web Store:
- **Chrome Group Policy (GPO)**:
  Use Google Chrome Enterprise ADMX templates: `ExtensionInstallForcelist` to push the extension ID or local `.crx`/folder path across all company machines.
- **Developer Mode (Unpacked)**:
  Open `chrome://extensions` -> enable **Developer mode** -> click **Load unpacked** -> select `c:\RPA Bots\extension`.

---

### 4. Configuring Extension Backend URL in Production

When users install the extension, they can connect it to your production domain:
1. Click the **MahaSetu RPA Recorder** icon in the Chrome toolbar.
2. Click the gear icon (`⚙`) in the popup header (or right-click extension -> **Options**).
3. Enter your deployed server URL (e.g., `https://rpa.yourdomain.com`).
4. Click **Test Ping** — the indicator turns green: `Connected (v1.0.0)`.
5. Click **Save** — all recorded workflows will now automatically export directly to your production cloud instance!

---

## Part 3: Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `5000` | Network port for web server |
| `HOST` | `0.0.0.0` | Network bind address |
| `FLASK_ENV` | `production` | Environment mode (`production` or `development`) |
| `SECRET_KEY` | *(random)* | Session encryption key |
| `CORS_ORIGINS` | `*` | Allowed CORS domains (e.g. `*` or `https://app.com`) |
| `PLAYWRIGHT_HEADLESS_DEFAULT` | `true` | Runs bots in headless mode by default on servers |
| `CHROME_PATH` | *(auto)* | Optional explicit path to Chrome binary |
| `WSGI_THREADS` | `8` | Worker thread count for production WSGI server |

---

## Part 4: Verification & Smoke Testing

To verify a fresh local or cloud deployment:

```bash
# Test local deployment
python verify_deployment.py

# Test remote cloud deployment
python verify_deployment.py --url https://rpa.yourdomain.com
```

All 10 automated verification checks will run and output a status report confirming:
- System Health API (`/api/health`)
- Security Headers (`X-Content-Type-Options`, `X-Frame-Options`)
- Web Views (`/builder`, `/extension-guide`, `/demo-target`)
- Extension Download Bundle Integrity (`/api/extension/download`)
- Bot Catalog & Payload Generators (JSON & XML)
- Extension Recording Ingestion Endpoint
- Headless Playwright Bot Execution Engine (both JSON and XML execution bodies)
