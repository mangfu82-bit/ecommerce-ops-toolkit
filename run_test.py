#!/usr/bin/env python3
"""运行 search 并保存日志"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import run_search
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

print("=" * 60)
print("电商运营工具包 - 运行日志")
print("=" * 60)

try:
    run_search()
    print("\n" + "=" * 60)
    print("运行完成！")
    print("=" * 60)
except Exception as e:
    logger.error(f"运行失败: {e}")
    import traceback
    traceback.print_exc()
