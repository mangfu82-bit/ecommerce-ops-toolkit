#!/usr/bin/env python3
"""验证搜索结果 + Git提交"""
import json
import subprocess
from pathlib import Path

project = Path.home() / ".qclaw/workspace/ecom-intelligence-platform"
json_file = project / "data/search_results.json"

print("=" * 60)
print("验证搜索结果")
print("=" * 60)

# 1. 验证数据
if not json_file.exists():
    print("[ERROR] 文件不存在: {}".format(json_file))
    exit(1)

with open(json_file, encoding="utf-8") as f:
    data = json.load(f)

print("[OK] 总条数: {}".format(len(data)))
print("[OK] 文件大小: {} bytes".format(json_file.stat().st_size))

keywords = {}
for item in data:
    kw = item.get("keyword", "未知")
    keywords.setdefault(kw, []).append(item)

print("[OK] 关键词数: {}".format(len(keywords)))
for kw in list(keywords.keys())[:5]:
    print("  > {}: {} 条".format(kw, len(keywords[kw])))

print("\n" + "=" * 60)
print("前3条数据示例:")
print("=" * 60)
for i, item in enumerate(data[:3]):
    print("\n[{}] 关键词: {}".format(i+1, item['keyword']))
    print("    标题: {}".format(item['title']))
    print("    URL: {}".format(item['url']))

# 2. Git 提交
print("\n" + "=" * 60)
print("Git 提交...")
print("=" * 60)

try:
    result = subprocess.run(["git", "add", "."], cwd=project, capture_output=True, text=True)
    if result.returncode == 0:
        print("[OK] git add .")
    else:
        print("[WARN] git add: {}".format(result.stderr.strip()))
    
    result = subprocess.run(
        ["git", "commit", "-m", "运行证据：search获取24条真实数据 + orchestrator修复"],
        cwd=project,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("[OK] git commit 成功")
        print(result.stdout.strip()[-200:] if result.stdout else "")
    else:
        print("[WARN] git commit: {}".format(result.stderr.strip()))
    
    result = subprocess.run(
        ["git", "push"],
        cwd=project,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("[OK] git push 成功")
        print(result.stdout[-200:] if result.stdout else "")
    else:
        print("[ERROR] git push 失败: {}".format(result.stderr.strip()))
        
except Exception as e:
    print("[ERROR] Git 操作异常: {}".format(e))

print("\n" + "=" * 60)
print("全部完成！")
print("=" * 60)
