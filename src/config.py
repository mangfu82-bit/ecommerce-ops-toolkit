"""
电商智能运营中台 - 配置管理
集中管理所有可配置参数，支持多 API Key 和多平台接入
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

# ========== 项目基础路径 ==========
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = PROJECT_ROOT / "cache"
RUNS_DIR = DATA_DIR / "runs"
VENDOR_DIR = DATA_DIR / "vendor"

for _dir in [DATA_DIR, LOGS_DIR, CACHE_DIR, RUNS_DIR, VENDOR_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# ========== LLM 配置 ==========
LLM_CONFIG = {
    # 主模型（搜索摘要、决策推荐）
    "primary": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "api_base": os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        "max_tokens": 2048,
        "temperature": 0.7,
    },
    # 备用模型（降级使用）
    "fallback": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "api_base": "https://api.deepseek.com/v1",
        "max_tokens": 2048,
        "temperature": 0.7,
    },
    # 分析专用（需要强推理时）
    "analysis": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "max_tokens": 4096,
        "temperature": 0.3,
    },
}

# 全局超时（秒）
LLM_TIMEOUT = 60
# 重试次数
LLM_MAX_RETRIES = 3


# ========== 平台配置 ==========
PLATFORMS = {
    "taobao": {
        "name": "淘宝闪购",
        "doc_prefix": "淘宝",
        "enabled": True,
        "api_key": os.getenv("TAOBAO_API_KEY", ""),
        "api_secret": os.getenv("TAOBAO_API_SECRET", ""),
    },
    "meituan": {
        "name": "美团闪购",
        "doc_prefix": "美团",
        "enabled": True,
        "api_key": os.getenv("MEITUAN_API_KEY", ""),
        "api_secret": os.getenv("MEITUAN_API_SECRET", ""),
    },
    "jd": {
        "name": "京东闪购",
        "doc_prefix": "京东",
        "enabled": True,
        "api_key": os.getenv("JD_API_KEY", ""),
        "api_secret": os.getenv("JD_API_SECRET", ""),
    },
    "douyin": {
        "name": "抖音闪购",
        "doc_prefix": "抖音",
        "enabled": True,
        "api_key": os.getenv("DOUYIN_API_KEY", ""),
        "api_secret": os.getenv("DOUYIN_API_SECRET", ""),
    },
}


# ========== 采集配置 ==========
CRAWLER_CONFIG = {
    # Bing 搜索（默认搜索方式）
    "bing": {
        "enabled": True,
        "api_key": os.getenv("BING_API_KEY", ""),
        "market": "zh-CN",
        "num_results": 10,
        "safe_search": "Moderate",
    },
    # 各平台 API（备用）
    "platform_api": {
        "taobao": {"enabled": False, "base_url": "https://eco.taobao.com"},
        "meituan": {"enabled": False, "base_url": "https://api.meituan.com"},
        "jd": {"enabled": False, "base_url": "https://api.jd.com"},
        "douyin": {"enabled": False, "base_url": "https://open.douyin.com"},
    },
}


# ========== 搜索关键词（按业务场景分组） ==========
SEARCH_KEYWORDS = [
    "淘宝闪购鲜花商家入驻攻略",
    "美团闪购鲜花运营技巧",
    "花漾美团鲜花平台商家入驻",
    "淘宝闪购商家版客户端后台管理",
    "美团闪购商家版客户端后台管理",
]


# ========== 知识库配置 ==========
KB_TITLE = "淘宝闪购加美团闪购鲜花运营"
KB_EMBEDDING_MODEL = "text-embedding-3-small"
KB_SIMILARITY_THRESHOLD = 0.6
KB_MAX_RESULTS = 10


# ========== 文档输出配置 ==========
DOC_CONFIG = {
    "link_list": "{prefix}闪购链接列表",
    "guide": "{prefix}闪购入驻攻略",
    "backend": "{prefix}商家后台操作指南",
    "huayang": "美团有花漾资料",
    "faq": "运营常见问题FAQ",
}


# ========== 工作流配置 ==========
WORKFLOW_CONFIG = {
    # 并行采集超时（秒）
    "collection_timeout": 30,
    # 融合层超时（秒）
    "fusion_timeout": 20,
    # 决策层超时（秒）
    "decision_timeout": 30,
    # 执行层超时（秒）
    "execution_timeout": 20,
    # 全局最大并发数
    "max_parallel_tasks": 4,
    # 审批阈值（超过此分数才自动执行，否则人工审批）
    "approval_threshold": 0.75,
    # 执行前是否强制审批
    "require_approval": True,
}


# ========== 监控配置 ==========
MONITOR_CONFIG = {
    "enable": True,
    # 告警级别阈值
    "alert_thresholds": {
        "price_drop_rate": 0.15,   # 价格下跌超过15%触发黄色告警
        "stock_low_rate": 0.2,     # 库存低于20%触发黄色告警
        "sentiment_negative_rate": 0.3,  # 差评率超过30%触发黄色告警
    },
    # 告警渠道
    "channels": ["log", "json"],
}


# ========== 日志配置 ==========
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
    "rotation": "daily",
    "retention_days": 30,
    "console": True,
    "file": True,
}


# ========== 知识库空间配置（腾讯文档） ==========
DOC_SPACE = {
    "space_id": os.getenv("DOC_SPACE_ID", ""),
    "title": "淘宝美团鲜花运营知识库",
    "default_folder": "运营资料",
}


# ========== 辅助函数 ==========
def is_llm_configured() -> bool:
    """检查 LLM 是否已配置至少一个可用的 API Key"""
    for key in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY"]:
        if os.getenv(key):
            return True
    return False


def get_enabled_platforms() -> List[str]:
    """返回所有已启用的平台列表"""
    return [k for k, v in PLATFORMS.items() if v.get("enabled")]


def get_llm_config_for_task(task_type: str = "primary") -> Dict:
    """根据任务类型获取合适的 LLM 配置"""
    if task_type in LLM_CONFIG:
        return LLM_CONFIG[task_type]
    return LLM_CONFIG["primary"]