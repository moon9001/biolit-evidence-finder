# Deployment Notes

This document covers running BioLitEvidence Finder on a fresh Linux,
macOS, or Windows host.

The README contains the everyday "I just want to run it locally" path.
DEPLOY.md focuses on multi-user / persistent / production-style
deployments.

---

## 1. Local clone-and-run (single user)

```bash
git clone https://github.com/<owner>/biolit-evidence-finder.git
cd biolit-evidence-finder

# Windows
start.bat

# Linux / macOS
bash start.sh
```

Open <http://localhost:5173>. First run installs dependencies (Python
venv + npm); subsequent runs reuse them.

---

## 2. Docker Compose

A minimal `docker-compose.yml` is included. It launches the backend in
a Python 3.11 container with `tesseract-ocr` and `tesseract-ocr-chi-sim`
preinstalled.

```bash
git clone https://github.com/<owner>/biolit-evidence-finder.git
cd biolit-evidence-finder

# Optional: provide LLM / embedding API keys
cp backend/.env.example backend/.env
# edit backend/.env

docker compose up -d --build
```

The backend listens on `:8000`. Run the frontend on the host alongside
it:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

To bake the frontend into the same compose file, add:

```yaml
  frontend:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app
    ports: ["5173:5173"]
    command: sh -lc "npm install && npm run dev -- --host 0.0.0.0"
    depends_on: [backend]
```

and change the proxy target in `frontend/vite.config.ts` to
`http://backend:8000`.

---

## 3. Production-style (systemd + nginx)

### Backend (systemd)

`/etc/systemd/system/biolit-backend.service`:

```ini
[Unit]
Description=BioLitEvidence Finder backend
After=network.target

[Service]
User=biolit
WorkingDirectory=/opt/biolit-evidence-finder/backend
EnvironmentFile=/opt/biolit-evidence-finder/backend/.env
Environment=DATA_DIR=/var/lib/biolit/data
Environment=DB_PATH=/var/lib/biolit/data/app.db
ExecStart=/opt/biolit-evidence-finder/backend/.venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now biolit-backend
journalctl -u biolit-backend -f
```

### Frontend (static build)

```bash
cd frontend
npm ci
npm run build
sudo mkdir -p /var/www/biolit
sudo cp -r dist/* /var/www/biolit/
```

### Nginx

```nginx
server {
    listen 80;
    server_name biolit.example.com;
    client_max_body_size 200m;

    root /var/www/biolit;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }

    location / {
        try_files $uri /index.html;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Run `certbot --nginx` to enable HTTPS.

---

## 4. Updating

```bash
cd biolit-evidence-finder
git pull

# backend
cd backend
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart biolit-backend

# frontend (static)
cd ../frontend
npm ci
npm run build
sudo cp -r dist/* /var/www/biolit/
```

---

## 5. Data management

```bash
cd backend

# JSON snapshot of all metadata (does not duplicate PDFs)
python scripts/export_data.py            # -> ./biolit_export.json
python scripts/export_data.py /path/out.json

# Wipe the database, FTS index, uploads and rendered images
python scripts/reset_data.py --yes
python scripts/reset_data.py --yes --backup   # snapshot first
```

---

## 6. LAN access

To let a colleague access the system from a different machine on the
same network:

1. Start the backend on `0.0.0.0`:
   `uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Start the frontend on `0.0.0.0`:
   `npm run dev -- --host 0.0.0.0 --port 5173`
3. Open the inbound firewall ports if necessary.
   Windows example (PowerShell as admin):
   ```powershell
   New-NetFirewallRule -DisplayName "BioLit 5173" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
   New-NetFirewallRule -DisplayName "BioLit 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```
4. Browse to `http://<host-LAN-IP>:5173`.

---

## 7. Troubleshooting

| Symptom | Resolution |
|---------|------------|
| `pytesseract not available` in logs | OS-level Tesseract is not installed; scanned PDFs will be skipped. Text-layer PDFs are unaffected. |
| Embedding API returns 401 | Verify `EMBEDDING_API_KEY` and that `EMBEDDING_API_BASE_URL` ends with `/v1` for OpenAI-compatible endpoints. |
| Browser cache shows old UI | Hard refresh (Ctrl+Shift+R) or open an incognito window. |
| Large PDF upload times out behind nginx | Raise `client_max_body_size` and `proxy_read_timeout`. |
