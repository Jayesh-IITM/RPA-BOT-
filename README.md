# MahaSetu - RPA Bot Ecosystem

An end-to-end platform to simplify setting up, recording, customizing, testing, and triggering Robotic Process Automation (RPA) Bots.

## Key Features

- **Chrome Extension (Manifest V3)**: Intelligent user action recorder with resilient multi-selector generation (ID, name, testid, CSS, XPath, text) and floating control bar.
- **Visual Flowchart Canvas**: Interactive workflow canvas with step inspection, variable binding (`{{username}}`), quick action insertion (`ADD WAIT`, `CAPTURE SCREENSHOT`), and branching outcome management.
- **Live TEST BOT Feature (Playwright)**: Launches Google Chrome in a visible window (`headless=False`), highlights active elements with visual boundaries, and streams real-time execution logs and screenshots via Server-Sent Events (SSE).
- **REST API Execution Engine**: Native JSON and XML execution payload support for triggering automated bot tasks programmatically.
- **Built-in Demo Target Portal**: Realistic portal (`/demo-target`) and dashboard (`/demo-dashboard`) for end-to-end testing with zero configuration.

## Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Start the Server
- **Development Server**:
  ```bash
  python start.py
  ```
- **Production WSGI Server (Waitress / Gunicorn)**:
  ```bash
  python start_production.py
  ```
- **Docker Deployment**:
  ```bash
  docker compose up --build -d
  ```
- **Railway.app Deployment**:
  See the 3-minute guide in [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md). Plug-and-play with pre-configured `railway.json` and Dockerfile.

### 3. Open the Workflow Builder
Access the Visual Builder in your browser:
- [http://127.0.0.1:5000/builder](http://127.0.0.1:5000/builder)
- Health API: [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)

### 4. Chrome Extension Installation & Distribution
- **Unpacked (Developer Mode)**:
  1. Open Google Chrome and navigate to `chrome://extensions`
  2. Enable **Developer mode** (top-right toggle)
  3. Click **Load unpacked** and select the extension folder: `c:\RPA Bots\extension`
- **Package for Chrome Web Store / Release**:
  ```bash
  python scripts/package_extension.py
  ```
  Creates `dist/mahasetu-rpa-recorder-v1.0.0.zip` ready for Chrome Web Store submission and in-portal download at `/api/extension/download`.

### 5. Run Verification & Automated Tests
```bash
# Complete end-to-end deployment verification (Health, Views, Extension ZIP, Bot Execution)
python verify_deployment.py

# Ecosystem verification suite (JSON & XML triggers)
python test_ecosystem.py

# Smart canvas gesture & resilient engine verification
python test_smart_engine.py
```

For comprehensive cloud, Docker, and Chrome Web Store guides, see [DEPLOYMENT.md](DEPLOYMENT.md).
