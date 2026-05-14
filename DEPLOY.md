# BioLitEvidence Finder — 部署与发布说明

本文档覆盖三件事：

1. 把项目从本地搬到另一台服务器（Linux 或 Windows）跑起来
2. 推送到 GitHub 私有仓库（论文发表前保密，发表后再公开）
3. 论文发表后转为公开仓库的操作

> ⚠️ **安全提示**
> Personal Access Token (`ghp_...`) 等同于密码，**不要写进任何文件，
> 不要贴进聊天/截图/issue/邮件**。如果不慎泄露，立刻到
> https://github.com/settings/tokens 撤销并重生成。
> 推荐用 **Fine-grained PAT**，只授权目标仓库 + `Contents: read/write`，
> 设最短有效期。

---

## 1. 项目初次推送到 GitHub（私有）

### 1.1 在 GitHub 上建空仓库

1. 打开 https://github.com/new
2. **Repository name**: `biolit-evidence-finder`（或任意名）
3. **Visibility**: 选 **Private**
4. 不要勾选 "Initialize with README"（我们本地已有）
5. 创建后记下 owner 和仓库名，例如 `your-username/biolit-evidence-finder`

### 1.2 在本地初始化 git 并提交

在项目根目录 `biolit-evidence-finder/` 下：

```bash
# 仅项目根目录这一层做 git init，DEPLOY.md 同级
git init
git add .
git commit -m "Initial commit: BioLitEvidence Finder MVP"
git branch -M main
```

确认 `.gitignore` 已经把这些排除了（已写好）：
- `.venv/`、`node_modules/`、`__pycache__/`、`dist/`
- `.env`（含 API key）
- `data/uploads/*`、`data/page_images/*`、`data/app.db*`

### 1.3 推送（**用环境变量传 token，不要写进 URL**）

#### 推荐做法 A：把 token 放进环境变量

Linux / macOS：
```bash
read -s -p "GitHub PAT: " GH_TOKEN; echo
git remote add origin "https://${GH_TOKEN}@github.com/<owner>/biolit-evidence-finder.git"
git push -u origin main
git remote set-url origin "https://github.com/<owner>/biolit-evidence-finder.git"
unset GH_TOKEN
```

Windows PowerShell：
```powershell
$tok = Read-Host -AsSecureString "GitHub PAT"
$plain = [System.Net.NetworkCredential]::new('', $tok).Password
git remote add origin "https://$plain@github.com/<owner>/biolit-evidence-finder.git"
git push -u origin main
git remote set-url origin "https://github.com/<owner>/biolit-evidence-finder.git"
Remove-Variable plain
```

最后一行把 remote URL 改回不带 token 的形式，避免 token 写进 `.git/config`。

#### 推荐做法 B：用 GitHub CLI（更省心）

```bash
# 安装 gh: https://cli.github.com/
gh auth login        # 交互式登录，token 安全保存在系统 keyring
gh repo create <owner>/biolit-evidence-finder --private --source . --push
```

#### 推荐做法 C：用 SSH key（长期最佳）

```bash
ssh-keygen -t ed25519 -C "your-email"
# 把 ~/.ssh/id_ed25519.pub 加到 https://github.com/settings/keys
git remote add origin git@github.com:<owner>/biolit-evidence-finder.git
git push -u origin main
```

### 1.4 验证保密性

推送完成后到仓库页面确认：
- 仓库右上角显示 **Private** 徽标
- `.env` **没有**出现在文件列表里
- `data/uploads/` 目录只有 `.gitkeep`

---

## 2. 在另一台服务器上跑起来

支持三种部署形态：

* **A. 本地直跑（开发/演示）**
* **B. Docker Compose（推荐用于服务器）**
* **C. systemd / nginx 反向代理（生产化）**

### 2.A 本地直跑（最简单）

#### 2.A.1 拉代码

```bash
git clone https://github.com/<owner>/biolit-evidence-finder.git
cd biolit-evidence-finder
```

如果是私有仓库，会弹出认证。**不要**用浏览器密码，用 PAT 或 SSH key
（参考 1.3）。

#### 2.A.2 后端

依赖：Python 3.11 / 3.12 / 3.13 任意一个。

Linux / macOS：
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 用任意编辑器填入 LLM_API_KEY / EMBEDDING_API_KEY 等（可留空）

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows：
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

测试接口：
```bash
curl http://127.0.0.1:8000/api/health
# {"status":"ok","service":"BioLitEvidence Finder"}

# 跑端到端冒烟（生成 demo PDF + 启动 + 测全部检索）
python scripts/create_demo_pdf.py demo.pdf
python scripts/smoke_test.py demo.pdf
```

##### 可选：本地 OCR

* **Linux (Debian/Ubuntu)**：
  ```bash
  sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim
  ```
* **macOS**：
  ```bash
  brew install tesseract tesseract-lang
  ```
* **Windows**：从 https://github.com/UB-Mannheim/tesseract/wiki 下载安装，
  把 `tesseract.exe` 加入 PATH，或在系统环境变量里指定。

不装也无所谓，扫描页会被静默跳过，普通 PDF 不受影响。

##### 可选：本地 sentence-transformers

```bash
pip install sentence-transformers
```

第一次运行会下载约 500 MB 的多语言模型缓存到 `~/.cache/huggingface/`。
不装则只有配置了 Embedding API 时才支持语义检索。

#### 2.A.3 前端

依赖：Node 18+。

```bash
cd ../frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

浏览器访问 `http://<服务器 IP>:5173`，注意服务器要放行 5173 / 8000 端口。

如果前后端不在同一台机器，编辑 `frontend/vite.config.ts`：

```ts
proxy: {
  '/api': { target: 'http://<backend-host>:8000', changeOrigin: true },
}
```

### 2.B Docker Compose（推荐）

仓库自带 `docker-compose.yml`。它会装 tesseract（含简体中文）。

```bash
git clone https://github.com/<owner>/biolit-evidence-finder.git
cd biolit-evidence-finder
cp backend/.env.example backend/.env   # 按需填写
docker compose up -d --build
```

后端跑在 `http://<host>:8000`，数据持久化到本地 `./data/`。

前端在 dev 阶段建议在主机上跑 `npm run dev`；如果要把前端也容器化，
把以下片段加到 `docker-compose.yml`：

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

并把 `vite.config.ts` 里 proxy target 改成 `http://backend:8000`。

### 2.C 生产化（systemd + nginx）

#### 后端 systemd 单元

`/etc/systemd/system/biolit-backend.service`：
```ini
[Unit]
Description=BioLitEvidence Finder backend
After=network.target

[Service]
User=biolit
WorkingDirectory=/opt/biolit-evidence-finder/backend
Environment=DATA_DIR=/var/lib/biolit/data
Environment=DB_PATH=/var/lib/biolit/data/app.db
EnvironmentFile=/opt/biolit-evidence-finder/backend/.env
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

#### 前端构建

```bash
cd frontend
npm ci
npm run build         # 生成 dist/
sudo mkdir -p /var/www/biolit
sudo cp -r dist/* /var/www/biolit/
```

#### nginx

```nginx
server {
    listen 80;
    server_name biolit.example.com;
    client_max_body_size 200m;            # 允许较大 PDF 上传

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

之后用 `certbot --nginx` 配 HTTPS 即可。

---

## 3. 服务器上更新代码

```bash
cd biolit-evidence-finder
git pull

# backend
cd backend
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart biolit-backend     # 或 docker compose up -d --build

# frontend (静态部署模式)
cd ../frontend
npm ci
npm run build
sudo cp -r dist/* /var/www/biolit/
```

数据库变更说明：本项目使用 SQLite，schema 改动后老表会自动 `create_all`，
但不会做迁移；如果改了 `models.py` 字段，要么手工 `ALTER TABLE`，
要么删掉 `data/app.db` 让其重建（会丢索引，原始 PDF 仍在 `data/uploads/`，
重新点 "重新处理" 即可）。

---

## 4. 论文发表后改公开

### 4.1 发布前最后清理（强烈建议）

公开前把仓库历史也过一遍，确保从来没有提交过敏感信息：

```bash
# 检查历史里是否出现过 .env、API key 字样
git log -p -- backend/.env 2>/dev/null | head
git log --all -p | grep -E "sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{30,}|API_KEY=" || echo "clean"
```

如果发现意外提交过 secret：
1. 立刻去对应平台撤销那条 key / token
2. 用 `git filter-repo` 或 https://rtyley.github.io/bgg/ 重写历史
3. `git push --force`

### 4.2 在仓库页面切换 Visibility

GitHub 仓库 → Settings → 拉到底 "Danger Zone" → **Change repository visibility** → Public。

### 4.3 给论文截图用的资源

公开后建议补几样：
- 在 README 顶部加论文 DOI / arXiv 链接
- 用 GitHub Release 打 `v0.1.0` tag，便于论文里写"版本号"
- 加 LICENSE（推荐 MIT 或 Apache-2.0；如果有学术引用诉求，可加 CITATION.cff）
- README 加一段 "How to cite"，给出 BibTeX

可以这样补一个 `CITATION.cff`：

```yaml
cff-version: 1.2.0
title: "BioLitEvidence Finder"
message: "If you use this software, please cite the following work."
type: software
authors:
  - family-names: "<你的姓>"
    given-names: "<你的名>"
version: 0.1.0
date-released: "YYYY-MM-DD"
url: "https://github.com/<owner>/biolit-evidence-finder"
```

---

## 5. 常见坑

| 现象 | 原因 / 处理 |
|------|------|
| `git push` 弹 401 / `Invalid username or token` | PAT 已过期或权限不足，重新生成 fine-grained token，给目标仓库 `Contents: read/write` |
| `ModuleNotFoundError: No module named 'app'` | 在 `scripts/` 下直接 `python xxx.py` 时未加 sys.path；统一从 `backend/` 目录运行 |
| `pytesseract not available` | 系统没装 tesseract，扫描页跳过即可，不影响普通 PDF |
| `Embedding API error 401` | `EMBEDDING_API_KEY` 错或 base URL 不带 `/v1` |
| 中文短词搜索 0 命中 | 已内置：FTS trigram 不支持 ≤2 字符 CJK 查询，自动 fallback 到 LIKE |
| 上传大 PDF 502 | nginx 加 `client_max_body_size 200m;` 并提高 `proxy_read_timeout` |
| 前端调用 8000 端口被代理拦截 (502) | 用 `httpx.Client(trust_env=False)` 或绕过系统代理；浏览器侧通常不受影响 |

---

## 6. 一页 quick reference

```bash
# === 私有仓库首推 ===
git init && git add . && git commit -m "init"
git branch -M main
gh auth login              # 用 GitHub CLI 最省心
gh repo create <owner>/biolit-evidence-finder --private --source . --push

# === 另一台服务器 ===
git clone https://github.com/<owner>/biolit-evidence-finder.git
cd biolit-evidence-finder
docker compose up -d --build       # 后端
cd frontend && npm ci && npm run dev -- --host 0.0.0.0   # 前端

# === 论文发表后 ===
# Settings → Change visibility → Public
# 加 LICENSE / CITATION.cff / README 引用段
```
