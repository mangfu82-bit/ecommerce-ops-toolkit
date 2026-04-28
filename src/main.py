"""
电商运营工具包 - 主入口

Usage:
    python src/main.py search        # 搜索运营资料
    python src/main.py build         # 生成文档
    python src/main.py all           # 完整流程
"""

import argparse
import json
import logging
import sys
from pathlib import Path

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


def run_search():
    """执行搜索任务"""
    logger.info("开始搜索...")
    logger.info(f"关键词: {SEARCH_KEYWORDS}")

    crawler = Crawler()
    results = crawler.search(SEARCH_KEYWORDS)

    # 导出到 JSON
    output_path = DATA_DIR / "search_results.json"
    crawler.export_json(str(output_path))

    # 打印前几条结果看看
    for i, r in enumerate(results[:5]):
        logger.info(f"  [{i+1}] {r.title}")
        logger.info(f"      {r.url}")

    logger.info(f"搜索完成，共获取 {len(results)} 条结果")
    return results


def run_build():
    """生成文档"""
    logger.info("开始生成文档...")

    # 读取搜索结果
    results_file = DATA_DIR / "search_results.json"
    if not results_file.exists():
        logger.warning("没有搜索结果，请先执行 search")
        return

    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    # 按 keyword 分组生成文档
    from collections import defaultdict
    groups = defaultdict(list)
    for r in results:
        groups[r["keyword"]].append(r)

    output_file = DATA_DIR / "knowledge_base.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {KB_TITLE} - 知识库\n\n")
        for kw, items in groups.items():
            f.write(f"## {kw}\n\n")
            for item in items:
                f.write(f"- **{item['title']}**\n")
                f.write(f"  {item['snippet']}\n")
                f.write(f"  链接: {item['url']}\n\n")

    logger.info(f"文档已生成: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="电商运营工具包")
    parser.add_argument("task", choices=["search", "build", "all"], help="任务类型")
    parser.add_argument("--keywords", nargs="*", help="自定义关键词（空格分隔）")

    args = parser.parse_args()

    if args.keywords:
        from src import config
        config.SEARCH_KEYWORDS = args.keywords

    if args.task == "search":
        run_search()
    elif args.task == "build":
        run_build()
    elif args.task == "all":
        run_search()
        run_build()
        logger.info("全部任务完成")


if __name__ == "__main__":
    main()
