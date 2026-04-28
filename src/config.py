# 平台配置和搜索关键词

# 搜索 API 地址（可选）
SEARCH_API_URL = ""  # 如需使用搜索 API，在此填写 URL

# 搜索关键词，按业务场景分组
SEARCH_KEYWORDS = [
    "淘宝闪购鲜花商家入驻攻略",
    "美团闪购鲜花运营技巧",
    "花漾美团鲜花平台商家入驻",
    "淘宝闪购商家版客户端后台管理",
    "美团闪购商家版客户端后台管理",
]

# 知识库标题
KB_TITLE = "淘宝闪购加美团闪购鲜花运营"

# 各平台配置
PLATFORMS = {
    "taobao": {
        "name": "淘宝闪购",
        "doc_prefix": "淘宝",
    },
    "meituan": {
        "name": "美团闪购",
        "doc_prefix": "美团",
    },
}

# 文档输出配置
DOC_CONFIG = {
    "link_list": "{prefix}闪购链接列表",
    "guide": "{prefix}闪购入驻攻略",
    "backend": "{prefix}商家后台操作指南",
    "huayang": "美团有花漾资料",
    "faq": "运营常见问题FAQ",
}
