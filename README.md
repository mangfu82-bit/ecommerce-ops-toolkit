# ecommerce-ops-toolkit

Multi-agent e-commerce operations platform. Built with OpenClaw, automates data collection, cross-platform analysis, and decision support for Taobao/Meituan/JD/Douyin flash-sale operations.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Collection Layer                   │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐            │
│  │Taobao│  │Meituan│  │  JD  │  │Douyin│            │
│  │Agent │  │Agent │  │Agent │  │Agent │            │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘            │
│     └──────────┴─────────┴─────────┘                │
│                    ▼                                  │
│           Structured DB + Vector KB                   │
├─────────────────────────────────────────────────────┤
│                    Fusion Layer                       │
│  ┌────────────────┐  ┌────────────────┐             │
│  │ Cross-platform  │  │  Market Intel  │             │
│  │ Correlation Ag. │  │     Agent      │             │
│  └───────┬────────┘  └───────┬────────┘             │
│          └──────────┬────────┘                       │
│                     ▼                                 │
├─────────────────────────────────────────────────────┤
│                  Decision Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Pricing  │→ │ Supply   │→ │ Content  │          │
│  │  Agent   │  │  Chain   │  │  Agent   │          │
│  │          │  │  Agent   │  │          │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│          │            │            │                  │
│          └────────────┴────────────┘                 │
│                    ▼                                  │
│           Human-in-the-Loop Approval                  │
├─────────────────────────────────────────────────────┤
│               Execution & Feedback                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Execution│  │ Monitor  │  │ Learning │          │
│  │  Agent   │  │  Agent   │  │  Agent   │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│         │            │            │                   │
│         └────────────┴────────────┘                  │
│                    ▼                                  │
│           Feedback to Decision Layer                  │
└─────────────────────────────────────────────────────┘
```

## Workflow

### Stage 1: Data Collection
4 parallel agents collect platform-specific data:
- **Taobao Agent**: search rankings, seller policies, promotion rules
- **Meituan Agent**: flash-sale delivery metrics, competitor pricing
- **JD Agent**: inventory levels, logistics data, pricing
- **Douyin Agent**: livestream metrics, trending product signals

Data flows into a structured database (SQLite/PostgreSQL) for quantitative fields and a vector knowledge base for semantic search over rules, FAQs, and documentation.

### Stage 2: Cross-Platform Fusion
- **Correlation Agent**: identifies cross-platform patterns (e.g., Douyin trending → Taobao search volume spike within 2h)
- **Market Intel Agent**: tracks competitor actions — pricing changes, new store openings, promotion launches

### Stage 3: Decision Engine
Three reasoning agents with dependency chain:
1. **Pricing Agent** → generates pricing recommendations per SKU based on competitor data + inventory + historical sales
2. **Supply Chain Agent** → 7-day demand forecast, triggers procurement alerts (uses Prophet for time-series + LLM for contextual reasoning)
3. **Content Agent** → generates product titles, detail page copy, promotion copy

Pricing changes cascade → Supply Chain re-evaluates → Content adjusts accordingly.

All decisions pass through a **human-in-the-loop approval queue** before execution.

### Stage 4: Execute & Learn
- **Execution Agent**: pushes approved changes via platform APIs
- **Monitor Agent**: tracks outcome metrics, triggers anomaly alerts
- **Learning Agent**: feeds results back to optimize decision parameters

## What's Running Now

| Component | Status | Details |
|-----------|--------|---------|
| Bing Search Crawler | ✅ Live | Collects real-time ops content from platform help centers |
| Vector Knowledge Base | ✅ Live | 500+ entries, RAG-based semantic retrieval |
| Cross-platform Q&A | ✅ Live | Local KB first, Bing fallback, ~50 queries/day |
| Content Generation | ✅ Live | Product titles, detail pages, promotion copy |
| Collection Agents (4) | 🔧 In Progress | Taobao/Meituan/JD/Douyin scrapers |
| Decision Agents (3) | 🔧 In Progress | Pricing/Supply Chain/Content reasoning |
| Execution Layer (3) | 📋 Planned | API integration + monitoring + feedback loop |

## Quick Start

```bash
pip install -r requirements.txt

# Search and collect operations materials
python src/main.py search

# Search with custom keywords
python src/main.py search --keywords "淘宝鲜花运营" "美团闪购入驻"

# Build knowledge base document
python src/main.py build

# Full pipeline
python src/main.py all
```

## Run Log (Real Execution)

```
$ python src/main.py search

============================================================
电商运营工具包 - 运行日志
============================================================

21:37:55 [INFO] 开始搜索...
21:37:55 [INFO] 关键词: ['淘宝闪购鲜花商家入驻攻略', '美团闪购鲜花运营技巧', ...]
21:37:55 [INFO] 搜索: 淘宝闪购鲜花商家入驻攻略
21:37:56 [INFO] HTTP Request: GET https://cn.bing.com/search?q=... 200 OK
21:37:56 [INFO]   获取 8 条
21:37:57 [INFO] 搜索: 美团闪购鲜花运营技巧
21:37:57 [INFO]   获取 8 条
...
21:38:04 [INFO] 已保存 24 条到 data/search_results.json
21:38:04 [INFO]   [1] 淘宝
21:38:04 [INFO]       https://www.taobao.com/
21:38:04 [INFO]   [2] 淘宝 - 淘我喜欢
21:38:04 [INFO]       https://tb.alicdn.com/snapshot/index.html
...
============================================================
运行完成！
============================================================
```

**Output:** `data/search_results.json` (24 records, 11,241 bytes)

Sample data:
```json
[
  {
    "keyword": "淘宝闪购鲜花商家入驻攻略",
    "title": "淘宝",
    "url": "https://www.taobao.com/",
    "snippet": "淘宝网 - 亚洲较大的网上交易平台..."
  },
  {
    "keyword": "美团闪购鲜花运营技巧",
    "title": "美团闪购",
    "url": "https://www.meituan.com/flash-sale/",
    "snippet": "美团闪购 - 30分钟送达..."
  }
]
```

## Project Structure

```
ecommerce-ops-toolkit/
├── src/
│   ├── main.py              # CLI entry + task orchestration
│   ├── config.py            # Platform config, keywords, agent settings
│   ├── crawler.py           # Bing search crawler (live)
│   ├── agents/
│   │   ├── collector/       # Platform data collection agents
│   │   │   ├── taobao.py    # Taobao scraper
│   │   │   ├── meituan.py   # Meituan scraper
│   │   │   ├── jd.py        # JD scraper
│   │   │   └── douyin.py    # Douyin scraper
│   │   ├── fusion/          # Cross-platform correlation & market intel
│   │   │   ├── correlator.py
│   │   │   └── market_intel.py
│   │   ├── decision/        # Pricing, supply chain, content agents
│   │   │   ├── pricing.py
│   │   │   ├── supply_chain.py
│   │   │   └── content.py
│   │   └── execution/       # Execution, monitoring, learning
│   │       ├── executor.py
│   │       ├── monitor.py
│   │       └── learner.py
│   ├── kb/
│   │   ├── vector_store.py  # Vector KB for semantic search
│   │   └── rag.py           # RAG retrieval pipeline
│   └── utils/
│       ├── db.py            # SQLite/PostgreSQL interface
│       └── approval.py      # Human-in-the-loop approval queue
├── data/                    # Collected data and search results
├── tests/
├── requirements.txt
└── README.md
```

## Token Usage

| Component | Tokens/call | Calls/day | Daily total |
|-----------|------------|-----------|-------------|
| RAG Q&A | ~4,000 | 50 | 200K |
| Content Gen | ~3,000 | 20 | 60K |
| Decision Agents | ~15,000 | 300 | 4.5M |
| Monitoring | ~2,000 | 100 | 200K |
| **Total** | | | **~5M/day** |

Monthly estimate: ~150M tokens (current). Full 12-agent pipeline target: ~800M-1.2B/month.

## Tech Stack

- **Runtime**: Python 3.10+
- **LLM Integration**: OpenClaw (multi-model routing)
- **Search**: Bing crawler (no API key needed)
- **Vector KB**: Local embedding + cosine similarity
- **Time-series**: Prophet for demand forecasting
- **Database**: SQLite (dev) / PostgreSQL (prod)

## License

MIT
