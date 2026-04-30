"""
电商智能运营中台 - 主入口
12-Agent 架构：采集层(4) + 融合层(2) + 决策层(3) + 执行层(3)

Usage:
    python src/main.py search                    # 搜索运营资料（Bing爬虫）
    python src/main.py build                     # 生成知识库文档
    python src/main.py demo                      # 运行演示工作流（生成运行记录）
    python src/main.py run [--keywords ...]      # 运行完整工作流
    python src/main.py list-runs                 # 列出历史运行记录
    python src/main.py status                    # 查看系统状态
    python src/main.py all                       # 完整流程：搜索+构建+演示
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SEARCH_KEYWORDS, KB_TITLE, PLATFORMS, DOC_CONFIG
from src.crawler import Crawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Main")

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def run_search(keywords=None):
    """执行搜索任务"""
    kw = keywords or SEARCH_KEYWORDS
    logger.info("=" * 60)
    logger.info("任务：搜索运营资料")
    logger.info(f"关键词数量: {len(kw)}")
    logger.info(f"关键词: {kw}")

    start = time.time()
    crawler = Crawler()
    results = crawler.search(kw)
    elapsed = round(time.time() - start, 2)

    # 导出到 JSON
    output_path = DATA_DIR / "search_results.json"
    crawler.export_json(str(output_path))

    # 统计
    domains = {}
    for r in results:
        from urllib.parse import urlparse
        domain = urlparse(r.get("url", "")).netloc
        domains[domain] = domains.get(domain, 0) + 1

    logger.info(f"搜索完成，耗时 {elapsed}秒")
    logger.info(f"结果总数: {len(results)}")
    logger.info(f"来源域名: {dict(list(sorted(domains.items(), key=lambda x: -x[1])))}")

    # 打印前5条
    logger.info("前5条结果预览:")
    for i, r in enumerate(results[:5]):
        logger.info(f"  [{i+1}] {r.get('title', 'N/A')}")
        logger.info(f"      {r.get('url', 'N/A')}")
        logger.info(f"      摘要: {r.get('snippet', '')[:80]}...")

    return results


def run_build():
    """生成知识库文档"""
    logger.info("=" * 60)
    logger.info("任务：生成知识库文档")

    results_file = DATA_DIR / "search_results.json"
    if not results_file.exists():
        logger.warning("没有搜索结果，请先执行 search")
        return

    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    logger.info(f"读取到 {len(results)} 条搜索结果")

    # 按 keyword 分组
    from collections import defaultdict
    groups = defaultdict(list)
    for r in results:
        kw = r.get("keyword", "其他")
        groups[kw].append(r)

    # 生成 Markdown
    output_file = DATA_DIR / "knowledge_base.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {KB_TITLE} - 知识库\n\n")
        f.write(f"> 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"共 {len(results)} 条资料，涵盖 {len(groups)} 个主题。\n\n")
        
        for kw, items in sorted(groups.items()):
            f.write(f"## {kw}\n\n")
            for item in items:
                f.write(f"### {item['title']}\n")
                f.write(f"**来源**: {item.get('source', '未知')}  \n")
                f.write(f"**链接**: {item['url']}  \n")
                f.write(f"**摘要**: {item.get('snippet', '无')}  \n")
                if item.get('timestamp'):
                    f.write(f"**时间**: {item['timestamp']}  \n")
                f.write("\n")

    logger.info(f"文档已生成: {output_file}")
    logger.info(f"文件大小: {output_file.stat().st_size} bytes")

    # 生成统计报告
    stats_file = DATA_DIR / "stats.json"
    stats = {
        "total_results": len(results),
        "keywords_count": len(groups),
        "generated_at": datetime.now().isoformat(),
        "top_domains": sorted(
            {r.get("source", "未知"): sum(1 for x in results if x.get("source") == r.get("source")) for r in results}.items(),
            key=lambda x: -x[1]
        )[:10]
    }
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    logger.info(f"统计报告已生成: {stats_file}")


def run_demo():
    """运行演示工作流（不依赖真实Agent）"""
    logger.info("=" * 60)
    logger.info("任务：演示工作流")
    logger.info("说明：生成模拟运行记录，展示系统能力")

    try:
        from src.core.orchestrator import Orchestrator
        o = Orchestrator({'data_dir': str(DATA_DIR)})
        result = o.run_demo()
        logger.info(f"演示完成: run_id={result['run_id']}, status={result['status']}")
        logger.info(f"步骤数: {len(result['steps'])}, 耗时: {result['total_duration']}秒")
        return result
    except Exception as e:
        logger.error(f"演示失败: {e}", exc_info=True)
        return None


def run_workflow(keywords=None):
    """运行完整工作流（需要真实Agent）"""
    logger.info("=" * 60)
    logger.info("任务：完整工作流")
    logger.warning("注意：当前为演示模式，Agent为模拟实现")

    try:
        from src.core.orchestrator import Orchestrator
        
        # 模拟注册Agent（实际项目中应从 src.agents 导入）
        class MockAgent:
            def __init__(self, name):
                self.name = name
            def run(self, keywords):
                from types import SimpleNamespace
                return SimpleNamespace(total=random.randint(5, 20), new_count=random.randint(3, 10))
        
        o = Orchestrator({'data_dir': str(DATA_DIR)})
        # 注册模拟Agent
        for name in ['taobao', 'meituan', 'jd', 'douyin']:
            o.register_collector(name, MockAgent(name))
        
        logger.info("开始执行工作流...")
        run_result = o.run_full_cycle(keywords or SEARCH_KEYWORDS, trigger="manual")
        
        logger.info(f"工作流完成: {run_result.run_id}")
        logger.info(f"状态: {run_result.status}")
        logger.info(f"成功步骤: {run_result.success_count}, 失败: {run_result.failed_count}")
        return run_result.to_dict()
    except Exception as e:
        logger.error(f"工作流失败: {e}", exc_info=True)
        return None


def list_runs():
    """列出历史运行记录"""
    logger.info("=" * 60)
    logger.info("任务：列出运行记录")

    runs_dir = DATA_DIR / "runs"
    if not runs_dir.exists():
        logger.info("没有运行记录")
        return

    runs = sorted(runs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    logger.info(f"共 {len(runs)} 条运行记录:\n")

    for i, run_file in enumerate(runs[:10]):  # 只显示最近10条
        with open(run_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"  [{i+1}] {data['run_id']} | {data['status']:10} | {data.get('total_duration', 0):5.2f}s | {data['trigger']}")
        logger.info(f"      步骤: {len(data['steps'])}, 成功: {data.get('success_count', 0)}, 失败: {data.get('failed_count', 0)}")


def show_status():
    """查看系统状态"""
    logger.info("=" * 60)
    logger.info("系统状态")
    
    # 检查目录
    dirs = {
        "data": DATA_DIR,
        "logs": LOGS_DIR,
        "data/runs": DATA_DIR / "runs",
        "src/agents": PROJECT_ROOT / "src" / "agents",
        "src/kb": PROJECT_ROOT / "src" / "kb",
        "src/utils": PROJECT_ROOT / "src" / "utils",
    }
    logger.info("目录检查:")
    for name, path in dirs.items():
        exists = "✓" if path.exists() else "✗"
        logger.info(f"  {exists} {name}: {path}")

    # 检查关键文件
    files = {
        "search_results.json": DATA_DIR / "search_results.json",
        "knowledge_base.md": DATA_DIR / "knowledge_base.md",
        "stats.json": DATA_DIR / "stats.json",
    }
    logger.info("数据文件:")
    for name, path in files.items():
        if path.exists():
            size = path.stat().st_size
            logger.info(f"  ✓ {name}: {size} bytes")
        else:
            logger.info(f"  ✗ {name}: 不存在")

    # 运行记录统计
    runs_dir = DATA_DIR / "runs"
    if runs_dir.exists():
        run_files = list(runs_dir.glob("*.json"))
        logger.info(f"运行记录: {len(run_files)} 条")
    else:
        logger.info("运行记录: 0 条")


def main():
    parser = argparse.ArgumentParser(
        description="电商智能运营中台 - 12-Agent 架构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python src/main.py search --keywords 鲜花 美团闪购
  python src/main.py demo
  python src/main.py run
  python src/main.py list-runs
        """
    )
    parser.add_argument("task", choices=["search", "build", "demo", "run", "list-runs", "status", "all"],
                        help="任务类型")
    parser.add_argument("--keywords", nargs="*", help="自定义关键词（空格分隔）")
    parser.add_argument("--verbose", action="store_true", help="详细日志")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.keywords:
        from src import config
        config.SEARCH_KEYWORDS = args.keywords
        logger.info(f"使用自定义关键词: {args.keywords}")

    start_time = time.time()
    
    if args.task == "search":
        run_search(args.keywords)
    elif args.task == "build":
        run_build()
    elif args.task == "demo":
        run_demo()
    elif args.task == "run":
        run_workflow(args.keywords)
    elif args.task == "list-runs":
        list_runs()
    elif args.task == "status":
        show_status()
    elif args.task == "all":
        logger.info("执行完整流程: search → build → demo")
        run_search(args.keywords)
        run_build()
        run_demo()
        logger.info("全部任务完成")

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"任务 {args.task} 完成，总耗时 {elapsed}秒")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
