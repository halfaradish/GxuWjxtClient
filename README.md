# gxu-wjxt — 广西大学文件管理系统 SDK (Python / Node.js)

[![GitHub](https://img.shields.io/badge/GitHub-仓库-238636?style=flat&logo=github&logoColor=fff&labelColor=000)](https://github.com/halfaradish/GxuWjxtClient) [![License](https://img.shields.io/github/license/halfaradish/GxuWjxtClient?style=flat)](https://github.com/halfaradish/GxuWjxtClient) [![Top Language](https://img.shields.io/github/languages/top/halfaradish/GxuWjxtClient?style=flat)](https://github.com/halfaradish/GxuWjxtClient) [![Last Commit](https://img.shields.io/github/last-commit/halfaradish/GxuWjxtClient?style=flat)](https://github.com/halfaradish/GxuWjxtClient)

[![PyPI](https://img.shields.io/pypi/v/gxu-wjxt?style=flat)](https://pypi.org/project/gxu-wjxt/)

---

[wjxt.gxu.edu.cn](https://wjxt.gxu.edu.cn) 的多语言 SDK，提供 API 封装、文件下载、数据解析。支持 Python（同步 + 异步）和 Node.js/TypeScript。

## 安装

### Python SDK

```bash
pip install gxu-wjxt
```

> 详细使用指南见 **[packages/python/GUIDE.md](packages/python/GUIDE.md)**，包含所有 API 用法、数据类参考、最佳实践和完整示例。

开发安装：

```bash
git clone https://github.com/halfaradish/GxuWjxtClient.git
cd GxuWjxtClient
pip install -e packages/python/
```

### Node.js SDK

```bash
npm install gxu-wjxt
# or
pnpm add gxu-wjxt
```

> 详细使用指南见 **[packages/node/GUIDE.md](packages/node/GUIDE.md)**。

开发安装：

```bash
git clone https://github.com/halfaradish/GxuWjxtClient.git
cd GxuWjxtClient
pnpm install
pnpm build:node
```

## 项目结构

```
.
├── pnpm-workspace.yaml         # pnpm 工作空间配置
├── package.json                # Monorepo 根配置
├── README.md
├── LICENSE
├── docs/
├── packages/
│   ├── python/                 # gxu-wjxt Python SDK
│   │   ├── pyproject.toml
│   │   ├── Makefile
│   │   ├── demo.py
│   │   ├── config.example.json
│   │   └── src/gxu_wjxt/       # 核心包（9个模块）
│   └── node/                   # gxu-wjxt TypeScript SDK
│       ├── package.json
│       ├── tsconfig.json
│       └── src/                # 核心包（7个模块）
```

## 快速开始

### 1. 配置凭证（三选一）

**方式 A — 配置文件：**

```bash
cp packages/python/config.example.json packages/python/config.json
# 编辑 config.json
```

```json
{"username": "your_student_id", "password": "your_password"}
```

**方式 B — 环境变量：**

```bash
export WJXT_USERNAME=your_student_id
export WJXT_PASSWORD=your_password
```

**方式 C — 直接传参（推荐）：**

```python
from gxu_wjxt import WjxtClient
client = WjxtClient(username="学号", password="密码")
```

### 2. 运行演示

```bash
python packages/python/demo.py
```

### 3. Node.js 快速体验

```typescript
import { WjxtClient } from 'gxu-wjxt';

const client = new WjxtClient({ username: 'student_id', password: 'password' });
await client.login();

// 遍历文件列表
for await (const file of client.iterFiles({ maxPages: 3 })) {
  console.log(`[${file.index}] ${file.department}: ${file.title}`);
}

// 搜索
const result = await client.search({ keyword: '通知', fileYear: '2026' });
console.log(`共 ${result.totalCount} 条，${result.totalPages} 页`);
```

## 使用方式

### Python 同步客户端

```python
from gxu_wjxt import WjxtClient

with WjxtClient(username="学号", password="密码") as client:
    client.login()

    # 获取部门列表
    depts = client.get_departments()
    for d in depts:
        print(f"[{d.id}] {d.tn_decoded}")

    # 获取分页文件列表
    files, page_info = client.get_file_list_structured(page=1)
    print(f"第{page_info.current_page}/{page_info.total_pages}页, "
          f"共{page_info.total_items}条")

    # 惰性遍历全部文件（自动翻页）
    for f in client.iter_files(max_pages=5):
        print(f"[{f.index}] {f.department}: {f.title} ({f.date})")

    # 获取文件详情
    detail = client.get_file_detail(file_id=61424)
    for att in detail.download_urls:
        print(f"  附件: {att.filename} -> {att.url}")

    # 下载文件
    path = client.download_file(file_id=61424, save_dir="./downloads")

    # 搜索文件
    result = client.search(keyword="奖学金", search_type="content")
    print(f"搜索到 {result.total_count} 条, 共 {result.total_pages} 页")
    for f in result.files[:5]:
        print(f"  [{f.index}] {f.department}: {f.title} ({f.date})")

    # 惰性遍历搜索结果（自动翻页）
    for f in client.iter_search(keyword="2026", file_year="2026", max_pages=3):
        print(f"{f.title}")

    # 业务办理
    page = client.get_todo_list()
    print(f"当前标签: {page.active_tab}, 导航: {list(page.nav_links.keys())}")
    if page.records:
        for r in page.records:
            print(f"  {r.cells}")
    if page.has_search:
        print("  支持搜索")

    # 电话簿
    contacts = client.parse_phone_list()
    for c in contacts:
        print(f"{c.name}: {c.phone}")

    client.logout()
```

### 异步客户端

```python
import asyncio
from gxu_wjxt import AsyncWjxtClient

async def main():
    async with AsyncWjxtClient(username="学号", password="密码") as client:
        await client.login()

        # 异步遍历文件列表
        async for f in client.iter_files(max_pages=3):
            print(f.title)

        await client.logout()

asyncio.run(main())
```

### 文件爬虫

```python
from gxu_wjxt import WjxtClient, FileCrawler

client = WjxtClient(username="学号", password="密码")
client.login()

crawler = FileCrawler(client, download_dir="./downloads", workers=3)

# 爬取全部（指定最大页数、仅未读）
stats = crawler.crawl_all(max_pages=5, unread_only=True)

# 按部门爬取
stats = crawler.crawl_department(dept_id=16, dept_name="学工部")

# 遍历所有部门
stats = crawler.crawl_all_departments(max_pages=3)

# 控制提前停止：连续 N 页无匹配记录时自动停止（默认 3，设 0 禁用）
stats = crawler.crawl_all(unread_only=True, max_empty_pages=5)

print(f"下载: {stats.downloaded}, 跳过: {stats.skipped}, 失败: {stats.failed}")
client.close()
```

### CLI 命令行

```bash
# pip install 后
gxu-wjxt -o ./downloads -d 16 -n 3 --workers 3

# 或
python -m gxu_wjxt.cli -o ./downloads -d all --dry-run

# 或使用模块方式
python -m gxu_wjxt.cli -o ./downloads --after 2026-03-01
```

| 参数 | 说明 |
|------|------|
| `-o, --output` | 下载目录（默认 `./downloads`） |
| `-d, --dept` | 部门 ID 或 `all` |
| `-n, --max-pages` | 最多爬取页数 |
| `--after` | 日期过滤 `YYYY-MM-DD` |
| `--unread-only` | 仅下载未读文件 |
| `--workers` | 并发线程数（默认 1） |
| `--max-empty-pages` | 连续 N 页无匹配时停止（默认 3，0 禁用） |
| `--dry-run` | 预览模式 |
| `-u, --username` | 用户名 |
| `-p, --password` | 密码 |

### 配置优先级

```
构造函数参数 > 环境变量 > 配置文件 > 默认值
```

```python
from gxu_wjxt import WjxtConfig

# 环境变量
config = WjxtConfig.from_env()

# 配置文件
config = WjxtConfig.from_file("config.json")

# 自定义
config = WjxtConfig(
    base_url="https://wjxt.gxu.edu.cn",
    myteip="172.28.222.133--2",
    timeout=30.0,
    retry_count=3,
    auto_relogin=True,          # 会话过期自动重连
    download_dir="./my_downloads",
)
```

### 输出目录结构

```
downloads/
├── download_history.json          # 下载记录（断点续爬）
├── 学工部（处）、武装部（就业中心）/
│   └── 2026-05-16_关于xxx通报/
│       ├── 2026-05-16_关于xxx通报.html    # 文件正文
│       ├── 附件1.doc
│       └── 附件2.xlsx
└── 校团委/
    └── ...
```

## API 覆盖

共 19 个端点，覆盖认证、文件管理、搜索、用户、电话簿、业务办理。Python 和 Node.js SDK 均覆盖全部端点。详见 [docs/api.md](docs/api.md)。

| 模块 | 端点 |
|------|------|
| 认证 | `Login.aspx`, `default.aspx`, `Exiting.aspx` |
| 主页/导航 | `Wjxt_UI/default.aspx`, `WebUI.aspx?id=2/4` |
| 文件管理 | `PageList.aspx`, `qstwj.aspx`, `showfile.aspx`, `Right.aspx` |
| 文件下载 | `/filezip/uploadfile/{year}/{month}/{filename}` |
| 搜索 | `search.aspx`, `filesearch.aspx`, `showdoc.aspx` |
| 用户管理 | `userEditPss.aspx` |
| 电话簿 | `phoneList.aspx` |
| 业务办理 | `business/business_MyToDoLists.aspx`、`business_DoList.aspx`、`business_MyUpLists.aspx`、`businessAdd.aspx` |

## 依赖

### Python SDK

- Python 3.10+
- [httpx](https://www.python-httpx.org/) — HTTP 客户端（同步+异步）
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) — HTML 解析

### Node.js SDK

- Node.js 18+
- [cheerio](https://cheerio.js.org/) — HTML 解析（等价 bs4）
- [iconv-lite](https://github.com/ashtuchkin/iconv-lite) — GB2312 编解码

## 注意事项

- 大量文件列表中约 50% 为纯文本公告，无附件可下载
- 默认 0.5 秒翻页间隔，避免对服务器造成压力
- 会话过期时自动重连（`auto_relogin=True`），对调用方透明
- `config.json` 包含敏感信息，已加入 `.gitignore`
- 客户端支持 `with` 语句自动关闭连接
