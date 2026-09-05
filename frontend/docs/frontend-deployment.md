# Frontend Build & Deployment Guide

## 1. Prerequisites
- **Node.js:** v18.0.0+ (Node 20+ recommended)
- **Package Manager:** `npm` (v9+) or `pnpm` / `yarn`
- **Backend Service:** FastAPI server running on `http://localhost:8000` (or production API host).

---

## 2. Environment Variables

Create a `.env` file in the root directory if overriding default proxy behavior:

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `/api` | Base path for API requests. In production, can point to direct origin e.g. `https://api.yourdomain.com`. |

---

## 3. Local Development

```bash
# 1. Install dependencies
npm install

# 2. Start Vite development server
npm run dev
```
The application will be accessible at `http://localhost:5173`.

---

## 4. Production Build & Static Hosting

```bash
# 1. Run TypeScript type checks and generate production build
npm run build

# 2. Preview production build locally
npm run preview
```

### 4.1 Deployment Targets
The output inside `dist/` consists entirely of static assets (HTML, CSS, JS, SVGs) and can be hosted on any static hosting provider:
- **Nginx / Apache:** Configure fallback to `/index.html` for client-side routing.
- **Vercel / Netlify / Cloudflare Pages:** Add rewrite rule `/* -> /index.html`.
- **AWS S3 + CloudFront:** Set error document to `index.html` with HTTP 200 response.

### 4.2 Nginx SPA Configuration Example
```nginx
server {
    listen 80;
    server_name merchant.yourdomain.com;
    root /var/www/razorpay-frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /events {
        proxy_pass http://localhost:8000/events;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```
