# ecommerce-ops-toolkit

多平台电商运营知识库管理工具。用于采集、整理和归档多平台（淘宝闪购、美团闪购等）的运营资料，自动生成结构化文档并同步到腾讯文档知识库。

## 功能

- 多关键词并行搜索，采集各平台运营资料
- 按平台和场景自动分类整理
- 生成标准化的运营文档（FAQ、操作指南、入驻攻略等）
- 一键同步到腾讯文档知识库空间

## 适用场景

- 新平台入驻时快速收集规则和资质要求
- 运营团队知识库搭建和维护
- 多平台资料对比和归档
- 新员工培训材料整理

## 项目结构

```
ecommerce-ops-toolkit/
├── src/
│   ├── crawler.py       # 搜索和数据采集
│   ├── doc_builder.py   # 文档内容生成
│   └── config.py        # 平台配置和搜索关键词
├── data/                # 采集到的原始数据
├── scripts/
│   └── build_kb.py      # 主入口：执行完整流程
├── requirements.txt
└── README.md
```

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

编辑 `src/config.py`，设置：

- `SEARCH_KEYWORDS`：要搜索的关键词列表
- `PLATFORMS`：目标平台配置
- `KB_TITLE`：知识库标题

### 运行

```bash
# 执行完整流程（搜索 → 整理 → 生成文档）
python scripts/build_kb.py

# 只搜索不生成文档
python scripts/build_kb.py --task search

# 指定自定义关键词
python scripts/build_kb.py --keywords "淘宝闪购入驻" "美团鲜花运营"
```

## 依赖

- Python 3.10+
- httpx（HTTP 请求）
- 腾讯文档 API（通过 MCP 或 SDK）

## 说明

本项目是运营团队内部使用的工具集，核心目的是把散落在各平台的运营规范、操作指南和常见问题收集整理成结构化知识库。代码结构简单，方便根据实际业务需求修改。

## License

MIT
