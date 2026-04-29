#!/usr/bin/env python3
import json
from pathlib import Path

project = Path.home() / ".qclaw/workspace/ecom-intelligence-platform"
json_file = project / "data/search_results.json"

print("=" * 60)
print("验证搜索结果数据")
print("=" * 60)

if not json_file.exists():
    print(f"[ERROR] 文件不存在: {json_file}")
    exit(1)

with open(json_file, encoding="utf-8") as f:
    data = json.load(f)

print(f"总条数: {len(data)}")
print(f"文件大小: {json_file.stat().st_size} bytes")
print()

# 按关键词分组
keywords = {}
for item in data:
    kw = item.get("keyword", "未知")
    if kw not in keywords:
        keywords[kw] = []
    keywords[kw].append(item)

print(f"关键词数: {len(keywords)}")
for kw, items in keywords.items():
    print(f"  - {kw}: {len(items)} 条")

print()
print("=" * 60)
print("前3条数据示例:")
print("=" * 60)
for i, item in enumerate(data[:3]):
    print(f"\n[{i+1}] 关键词: {item['keyword']}")
    print(f"    标题: {item['title']}")
    print(f"    URL: {item['url']}")
    print(f"    摘要: {item['snippet'][:80]}...")

print("\n验证完成！")
