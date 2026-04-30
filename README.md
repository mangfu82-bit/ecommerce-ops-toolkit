# E-commerce Intelligent Ops Platform

LLM-powered intelligent e-commerce operations platform for cross-platform data collection, analysis and automated decision-making.

Supports: Taobao, Meituan Flash, JD, Douyin

## Architecture

```
Trigger → Collection (4 platforms parallel) → Fusion (LLM) → Decision (LLM) → Execution → Report
```

**8-stage workflow:**
1. Trigger: Scheduled / API / Manual
2. Collection: 4 platforms in parallel (Taobao / Meituan / JD / Douyin)
3. Cleaning: LLM deduplication + relevance scoring
4. Fusion: Cross-platform analysis + knowledge graph
5. Decision: Multi-dimensional scoring + action recommendation
6. Execution: Multi-strategy execution + retry
7. Approval: Human-in-the-loop confirmation
8. Review: LLM self-evaluation + optimization

## Modules

### Core
- `src/core/orchestrator.py` - 8-stage async parallel workflow
- `src/core/llm_router.py` - Multi-model routing (GPT-4o-mini / DeepSeek / GPT-3.5)
- `src/core/retry_engine.py` - Smart retry with exponential backoff

### Collection Layer (LLM-powered)
- `src/agents/collector/taobao.py` - Product search, store analysis, price monitoring
- `src/agents/collector/meituan.py` - Flash sale, delivery zones, competitor tracking
- `src/agents/collector/jd.py` - Product data, reviews, price history
- `src/agents/collector/douyin.py` - Live streaming, short videos, influencer analysis

### Fusion Layer
- `src/agents/fusion/correlator.py` - Price arbitrage, cross-platform matching
- `src/agents/fusion/market_intel.py` - Market trends, competitive intelligence

### Decision Layer
- `src/agents/decision/pricing.py` - Dynamic pricing strategy (17KB, LLM-powered)
- `src/agents/decision/supply_chain.py` - Inventory management, procurement
- `src/agents/decision/content.py` - Product listing optimization

### Execution Layer
- `src/agents/execution/executor.py` - Task execution engine with retry
- `src/agents/execution/monitor.py` - Real-time monitoring and alerting

## Quick Start

```bash
# One-click demo
python demo.py

# Search command
python src/main.py search "rose bouquet mothers day"

# Run status
python src/main.py status

# List runs
python src/main.py list-runs
```

## Configuration

Copy and edit config:
```bash
cp config.EXAMPLE.yaml config.yaml
```

## Demo Output

```
[Stage 1/4] Collection layer - 4 platforms parallel...
  [Taobao] searching...
  [Meituan] searching...
  [JD] searching...
  [Douyin] searching...
  Collected: 20 items

[Stage 2/4] Fusion layer - LLM cross-platform analysis...
  Total products: 20
  Average price: 83.80
  Top platform: Taobao

[Stage 3/4] Decision layer - Generate ops decisions...
  Decision: price_adjust
  Platform: Taobao
  Suggestion: Adjust price 1% on Taobao
  Approval: required

[Stage 4/4] Execution report
  Run ID: demo_20260XXX_XXXXXX
  Status: completed
  Duration: 12.5s
```

## Project Stats

| Layer | Files | Size |
|-------|-------|------|
| Core | 3 | 30KB |
| Collection | 4 | 51KB |
| Fusion | 2 | 31KB |
| Decision | 3 | 53KB |
| Execution | 2 | 20KB |
| **Total** | **14** | **~185KB** |

## License

MIT

## GitHub

https://github.com/mangfu82-bit/ecommerce-ops-toolkit