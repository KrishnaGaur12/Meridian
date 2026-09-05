# Backend Deployment & Infrastructure Guide

## 1. Local Development Setup

### 1.1 Prerequisites
- Python `3.11+` (Verified on Python `3.13.1`)
- Git

### 1.2 Installation Steps
```bash
# 1. Clone repository
git clone <repo_url>
cd "AI Chargeback Evidence Responce"

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 3. Install production dependencies
pip install -r requirements.txt

# 4. Configure environment variables (optional for live DeepSeek AI)
cp .env.example .env
# Edit .env and set DEEPSEEK_API_KEY=your_key_here
```

### 1.3 Running the Development Server
```bash
uvicorn main:app --reload --port 8000
```
- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Swagger Docs: `http://localhost:8000/docs`
- Alternative Redoc Documentation: `http://localhost:8000/redoc`

---

## 2. CLI Execution Mode

The backend can be run in standalone CLI mode without running an HTTP server:

```bash
# Run one of the 5 seeded dispute scenarios
python main.py --scenario 1  # CONTEST scenario (High win probability)
python main.py --scenario 2  # ACCEPT scenario (Missing tracking proof)
python main.py --scenario 3  # INVESTIGATE scenario (Appliance dispute)
python main.py --scenario 4  # HIGH FRAUD scenario (Velocity risk)
python main.py --scenario 5  # DUPLICATE CHARGE scenario

# Run on custom JSON file
python main.py --dispute path/to/dispute.json

# Output raw JSON
python main.py --scenario 1 --json
```

---

## 3. Production Deployment Specification

### 3.1 Production Server Command
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='*'
```

### 3.2 Environment Variables

| Variable | Required | Default Value | Description |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | Optional | `""` | DeepSeek LLM API Key (if omitted, falls back to deterministic rule generators). |
| `DEEPSEEK_BASE_URL` | Optional | `https://api.deepseek.com` | DeepSeek OpenAI-compatible base URL. |
| `DEEPSEEK_MODEL` | Optional | `deepseek-chat` | DeepSeek model identifier. |
| `DEEPSEEK_TIMEOUT_SECONDS` | Optional | `15` | Maximum HTTP timeout for AI requests. |
| `AI_CACHE_TTL_SECONDS` | Optional | `3600` | In-memory cache duration in seconds. |
| `OLLAMA_URL` | Optional | `http://localhost:11434` | URL for local Ollama server if enabled. |
| `OLLAMA_DEFAULT_MODEL` | Optional | `llama3.2` | Local model name for Ollama. |

### 3.3 Health Checks & Monitoring
- **Liveness Probe**: `GET /health` (Returns HTTP 200 `{"status": "ok"}`).
- **ML Metric Probe**: `GET /ml/model-health` (Returns validation metrics and baseline health).
- **System Mode Probe**: `GET /system/mode` (Verifies database file connectivity and mode).
