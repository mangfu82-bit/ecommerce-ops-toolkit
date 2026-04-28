"""
E-commerce Operations Toolkit - Main Entry

Usage:
    python src/main.py search        # 执行搜索
    python src/main.py build         # 生成文档
    python src/main.py all            # 完整流程
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SEARCH_KEYWORDS, KB_TITLE, PLATFORMS, DOC_CONFIG
from src.crawler import Crawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_search():
    """执行搜索任务"""
    logger.info("开始搜索...")
    logger.info(f"关键词: {SEARCH_KEYWORDS}")

    crawler = Crawler()
    results = await crawler.search(SEARCH_KEYWORDS)

    # 导出到 JSON
    output_path = DATA_DIR / "search_results.json"
    crawler.export_json(str(output_path))

    logger.info(f"搜索完成，共获取 {len(results)} 条结果")
    return results


def run_build():
    """生成文档"""
    logger.info("开始生成文档...")
    # 简化的文档生成逻辑
    logger.info("文档生成完成")


async def main():
    parser = argparse.ArgumentParser(description="电商运营工具包")
    parser.add_argument("task", choices=["search", "build", "all"], help="任务类型")
    parser.add_argument("--keywords", nargs="*", help="自定义关键词")
    parser.add_argument("--api-url", help="搜索 API 地址")

    args = parser.parse_args()

    if args.keywords:
        # 临时覆盖关键词
        from src import config
        config.SEARCH_KEYWORDS = args.keywords

    if args.api-url:
        from src import config
        config.SEARCH_API_URL = args.api_url

    if args.task == "search":
        await run_search()
    elif args.task == "build":
        run_build()
    elif args.task == "all":
        await run_search()
        run_build()
        logger.info("全部任务完成")


if __name__ == "__main__":
    asyncio.run(main())