# BioLitEvidence Finder

> Page-level evidence discovery for biodiversity literature.
> 面向植物分类学、生物多样性文献、地方植物志、专著与图谱 PDF 的页级证据发现原型。

核心目标是：让研究者上传一批 PDF，系统按页拆解文本与图像，
自动识别拉丁学名 / 中文关键词 / 主题词，建立 “PDF 文献—页面—名称—证据片段” 索引，
并支持 **关键词、学名、全文、语义、混合** 五种检索模式。每条检索结果都保留
**文档名 + 页码 + 命中词 + 上下文 + 原文回查链接**，便于论文截图与人工验证。

本项目刻意保持 **离线优先**：

* 没有 LLM API 时 → 规则抽取依然工作。
* 没有 Embedding API 时 → 尝试本地 `sentence-transformers`，再降级为关键词与 FTS5。
* 没有 OCR / tesseract 时 → 仅处理带文本层的 PDF，扫描页静默跳过。

---

## 1. 项目结构

```
biolit-evidence-finder/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI 入口
│   │   ├── config.py              # .env 配置 + 运行时可改
│   │   ├── database.py            # SQLAlchemy + FTS5 初始化
│   │   ├── models.py              # documents/pages/occurrences/chunks/search_logs
│   │   ├── schemas.py             # Pydantic IO
│   │   ├── routers/
│   │   │   ├── documents.py
│   │   │   ├── search.py
│   │   │   ├── settings.py
│   │   │   └── stats.py
│   │   └── services/
│   │       ├── pdf_service.py     # PyMuPDF 文本抽取 + 页截图 + 流水线
│   │       ├── ocr_service.py     # pytesseract，可选
│   │       ├── extraction_service.py  # 拉丁学名 / 中文关键词规则
│   │       ├── llm_service.py     # OpenAI 兼容 LLM 抽取
│   │       ├── embedding_service.py   # API 优先，本地兜底
│   │       ├── search_service.py  # exact / scientific / fts / semantic / hybrid
│   │       └── export_service.py  # CSV / JSON 导出
│   ├── scripts/
│   │   └── create_demo_pdf.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/  (Dashboard, Upload, Documents, Search, Viewer, Settings)
│   │   ├── components/StatusBadge.tsx
│   │   ├── api/client.ts
│   │   ├── types/index.ts
│   │   ├── App.tsx + main.tsx
│   │   └── index.css
│   ├── package.json / tsconfig / vite.config / tailwind.config / postcss.config
│   └── index.html
├── data/
│   ├── uploads/        # 原始 PDF
│   ├── page_images/    # 每页截图（PNG）
│   └── app.db          # SQLite，含 FTS5 虚拟表
├── docker-compose.yml
└── README.md
```

---

## 2. 启动

### 后端

```bash
cd biolit-evidence-finder/backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate
pip install -r requirements.txt

# （可选）配置 LLM / Embedding
cp .env.example .env
# 填写 LLM_API_BASE_URL / LLM_API_KEY / LLM_MODEL 等

uvicorn app.main:app --reload --port 8000
```

OpenAPI: http://127.0.0.1:8000/docs

### 前端

```bash
cd biolit-evidence-finder/frontend
npm install
npm run dev
```

访问 http://localhost:5173

`vite.config.ts` 已经把 `/api` 代理到 `http://127.0.0.1:8000`。

### Docker（可选）

```bash
docker-compose up --build
```

Compose 仅启动后端容器（轻量 OCR/嵌入栈），前端保持本地 `npm run dev`
以便随时改 UI。

---

## 3. 演示数据 / 自测

仓库已附带 `backend/scripts/create_demo_pdf.py`。该脚本会生成一份包含
`Camellia sinensis`、`Camellia reticulata`、`Rosa chinensis` 与若干中文关键词
的小型 PDF（5 页），用于检索冒烟测试。

```bash
cd biolit-evidence-finder/backend
.venv\Scripts\activate
python scripts/create_demo_pdf.py demo.pdf
```

然后在前端 **上传 PDF** 页选 `demo.pdf` 上传。处理完成后：

1. 在 **检索** 页输入 `Camellia sinensis`，模式选 `学名检索`。
2. 命中结果应显示文献名、页码（约第 2 页）、上下文以及 “查看原文 →” 链接。
3. 点击进入 **Viewer**：左侧为该页 PNG 截图，右侧为页面文本，
   关键词按高亮显示。
4. 点击 “打开原始 PDF”，浏览器原生 PDF 视图按 `#page=2` 直接跳页。
5. 输入 `茶树在哪些页面出现`，模式选 `语义检索` / `混合检索`，
   即可看到自然语言问答样式的页级命中（需启用 Embedding API 或本地模型）。

---

## 4. 关键 API 示例

```bash
# 上传 PDF
curl -X POST http://127.0.0.1:8000/api/documents/upload \
  -F "files=@demo.pdf"

# 文献列表
curl http://127.0.0.1:8000/api/documents

# 触发重新解析
curl -X POST http://127.0.0.1:8000/api/documents/1/process

# 关键词检索（默认混合）
curl "http://127.0.0.1:8000/api/search?q=Camellia%20sinensis&mode=hybrid"

# 学名检索
curl "http://127.0.0.1:8000/api/search?q=Camellia&mode=scientific"

# 全文检索（FTS5）
curl "http://127.0.0.1:8000/api/search?q=%E8%8C%B6%E6%A0%91&mode=fulltext"

# 语义检索
curl "http://127.0.0.1:8000/api/search?q=%E4%BA%91%E5%8D%97%E5%B1%B1%E8%8C%B6%E5%88%86%E5%B8%83&mode=semantic"

# 导出 CSV
curl -OJ "http://127.0.0.1:8000/api/export/search-results?q=Camellia&mode=hybrid&format=csv"

# 当前能力状态
curl http://127.0.0.1:8000/api/settings/status
```

返回示例（节选）：

```json
{
  "query": "Camellia sinensis",
  "mode": "hybrid",
  "result_count": 1,
  "results": [{
    "document_id": 1,
    "document_title": "demo.pdf",
    "file_name": "demo.pdf",
    "page_number": 2,
    "matched_term": "Camellia sinensis",
    "context": "Camellia sinensis (L.) Kuntze 是世界上最重要的经济作物之一 ...",
    "score": 0.93,
    "match_type": "scientific_name",
    "viewer_url": "/viewer/1?page=2&q=Camellia%20sinensis&mode=hybrid"
  }]
}
```

---

## 5. 已实现功能清单

* PDF 上传（多文件、`auto_process` 自动入队）
* PyMuPDF 逐页文本抽取 + 页截图（DPI 可配）
* OCR 兜底：pytesseract，环境缺失时自动跳过
* 规则抽取：拉丁二名法 / 种下等级 / 缩写学名 / 中文分类术语 / 中文常见名后缀 / 主要省份地名
* LLM 抽取（可选，OpenAI 兼容 `/chat/completions`），有页面文本对照防幻觉
* SQLite + WAL，外加 FTS5 虚拟表 (`pages_fts`) 用于全文检索
* 语义切片：按段落/字符切分，每页生成 chunks
* Embedding：API 优先（`/embeddings`），fallback 到本地 `sentence-transformers`
* 五种检索：精确 / 学名 / FTS / 语义 / 混合，统一返回结构 + viewer URL
* 检索结果导出：CSV、JSON
* 前端：Dashboard、Upload、Documents（实时刷新状态）、Search、Viewer
  （左截图 / 右文本，关键词高亮）、Settings（运行时改 API 配置 + 测试连接）
* `/api/health`、`/api/stats`、`/api/settings/status` 健康与能力上报

---

## 6. 后续可扩展方向

1. **页面坐标级高亮**：用 `page.search_for(term)` 拿命中矩形，
   在前端 Viewer 把矩形画到截图上。
2. **DeepSeek-OCR 全文档转 Markdown**：当前留有 `DEEPSEEK_OCR_URL` 配置位，
   可在 `pdf_service` 中接入 `convert + result` 轮询接口替代 tesseract。
3. **Reranker（如 `qwen3-reranker:8b`）**：混合检索结果交给 reranker 二次打分。
4. **真正的向量库**：当语料超过百万 chunk 时迁移到 FAISS / pgvector。
5. **批量元数据补全**：用 LLM 阅读首页提取标题、作者、年份。
6. **图版 / 形态特征结构化**：识别 “图版 / Plate / Fig.” 段落，
   入库为单独的 `figure_evidence` 类型。
7. **多用户 / ACL**：按项目和团队隔离上传与索引。
8. **可点击高亮坐标 + 双向跳转**：前端从 Viewer 截图直接点击坐标 → 后端解析对应 occurrences。

---

## 7. 故障排查

* `pytesseract not available` —— 系统未安装 tesseract，扫描 PDF 不会做 OCR；普通 PDF 不受影响。
* `Embedding API error` —— 检查 `EMBEDDING_API_BASE_URL` 是否指向 OpenAI 兼容根（通常以 `/v1` 结尾）。
* `LLM 输出非 JSON` —— 已在 `llm_service` 内部做 markdown 去除与 JSON 提取，模型偶发越权回复时该页直接退化为规则抽取，不会破坏流水线。
* `SQLite FTS5 query syntax` —— 用户输入会被 token 化后包装成短语查询，特殊字符不会触发 FTS5 错误。
