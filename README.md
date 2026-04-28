# ecommerce-ops-toolkit

Multi-platform e-commerce operations knowledge base management tool. Collects, organizes and archives operations materials from multiple platforms (Taobao Flash Sale, Meituan Flash Sale, JD, Douyin, etc.), generates structured documents and syncs to Tencent Docs knowledge base.

## Features

- Multi-keyword parallel search, collect operations materials from each platform
- Automatic classification by platform and scenario
- Generate standardized operations documents (FAQ, operation guides, onboarding guides, etc.)
- One-click sync to Tencent Docs knowledge base space
- Bing real-time search integration for latest platform announcements and rule changes

## Project Structure

```
ecommerce-ops-toolkit/
├── src/
│   ├── main.py          # CLI entry point and Bing search crawler
│   └── config.py         # Platform configuration and search keywords
├── data/                 # Collected raw data and search results
├── requirements.txt
└── README.md
```

## Usage

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configuration

Edit `src/config.py`:

- `SEARCH_KEYWORDS`: List of keywords to search
- `PLATFORMS`: Target platform configuration
- `KB_TITLE`: Knowledge base title

### Run

```bash
# Run search and save results to data/search_results.json
python src/main.py search

# Search with custom keywords
python src/main.py search --keywords "淘宝鲜花运营" "美团闪购入驻"

# Specify API endpoint (optional, Bing crawler used by default)
python src/main.py search --api-url "http://your-api-endpoint.com"
```

## Architecture

The tool follows a simple two-layer architecture:

1. **Data Collection Layer**: Bing search crawler fetches real-time operations content from platform help centers, support forums, and industry sources
2. **Knowledge Base Layer**: Structured JSON storage with full-text search capability, ready for integration with external knowledge base systems

## Dependencies

- Python 3.10+
- httpx (HTTP client)
- rich (CLI output formatting)

## Notes

Core purpose: collect and organize operations specs, operation guides and FAQs scattered across multiple platforms into structured knowledge bases. Code structure is simple and easy to modify according to actual business needs.

## License

MIT
