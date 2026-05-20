# gxu-wjxt Python SDK 使用指南

> 广西大学文件管理系统 Python SDK 完整使用文档

---

## 目录

1. [安装](#1-安装)
2. [配置](#2-配置)
3. [同步客户端 WjxtClient](#3-同步客户端-wjxtclient)
   - [3.1 生命周期](#31-生命周期)
   - [3.2 认证](#32-认证)
   - [3.3 部门列表](#33-部门列表)
   - [3.4 文件列表与遍历](#34-文件列表与遍历)
   - [3.5 文件详情与下载](#35-文件详情与下载)
   - [3.6 搜索](#36-搜索)
   - [3.7 电话簿](#37-电话簿)
   - [3.8 密码修改](#38-密码修改)
   - [3.9 业务办理](#39-业务办理)
4. [异步客户端 AsyncWjxtClient](#4-异步客户端-asyncwjxtclient)
5. [文件爬虫 FileCrawler](#5-文件爬虫-filecrawler)
   - [5.1 基本用法](#51-基本用法)
   - [5.2 爬取策略](#52-爬取策略)
   - [5.3 过滤与提前停止](#53-过滤与提前停止)
   - [5.4 多线程下载](#54-多线程下载)
   - [5.5 下载记录与断点续爬](#55-下载记录与断点续爬)
   - [5.6 输出目录结构](#56-输出目录结构)
6. [数据类参考](#6-数据类参考)
7. [异常处理](#7-异常处理)
8. [CLI 命令行](#8-cli-命令行)
9. [最佳实践](#9-最佳实践)

---

## 1. 安装

```bash
pip install gxu-wjxt
```

开发安装（可编辑模式）：

```bash
git clone https://github.com/halfaradish/GxuWjxtClient.git
cd GxuWjxtClient
pip install -e packages/python/
```

**依赖：** Python 3.10+，httpx >= 0.27.0，beautifulsoup4 >= 4.12.0

---

## 2. 配置

SDK 提供三种配置方式，优先级为：**构造函数参数 > 环境变量 > 配置文件 > 默认值**。

### 方式 A：构造函数传参（推荐）

```python
from gxu_wjxt import WjxtClient, WjxtConfig

# 直接传参
client = WjxtClient(username="2407110315", password="your_password")

# 使用配置对象
config = WjxtConfig(
    username="2407110315",
    password="your_password",
    timeout=60.0,
    download_dir="./my_downloads",
)
client = WjxtClient(config=config)
```

### 方式 B：环境变量

```bash
export WJXT_USERNAME=2407110315
export WJXT_PASSWORD=your_password
export WJXT_BASE_URL=https://wjxt.gxu.edu.cn   # 可选
export WJXT_MYTEIP=172.28.222.133--2            # 可选
export WJXT_DOWNLOAD_DIR=./downloads            # 可选
```

```python
from gxu_wjxt import WjxtConfig

config = WjxtConfig.from_env()
client = WjxtClient(config=config)
```

### 方式 C：配置文件

创建 `config.json`（项目目录）或 `~/.gxu_wjxt.json`（用户目录）：

```json
{
    "username": "2407110315",
    "password": "your_password",
    "base_url": "https://wjxt.gxu.edu.cn",
    "myteip": "172.28.222.133--2",
    "download_dir": "./downloads"
}
```

```python
from gxu_wjxt import WjxtConfig

config = WjxtConfig.from_file("config.json")
client = WjxtClient(config=config)
```

### WjxtConfig 完整字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `username` | `str` | `""` | 学号/用户名 |
| `password` | `str` | `""` | 密码 |
| `base_url` | `str` | `"https://wjxt.gxu.edu.cn"` | 系统根地址 |
| `myteip` | `str` | `"172.28.222.133--2"` | 办公 IP 标识 |
| `timeout` | `float` | `30.0` | HTTP 请求超时（秒） |
| `max_redirects` | `int` | `5` | 最大重定向次数 |
| `verify_ssl` | `bool` | `False` | SSL 证书验证 |
| `retry_count` | `int` | `3` | 请求失败重试次数 |
| `retry_delay` | `float` | `2.0` | 重试间隔（秒） |
| `download_dir` | `str` | `"./downloads"` | 默认下载目录 |
| `page_delay` | `float` | `0.5` | 翻页间隔（秒） |
| `history_file` | `str` | `"download_history.json"` | 下载记录文件名 |
| `max_workers` | `int` | `1` | 并发线程数 |
| `user_agent` | `str` | Chrome 120 UA | HTTP User-Agent |

`merge_with(**kwargs)` 方法可基于当前配置创建覆盖副本：

```python
prod_config = config.merge_with(timeout=60.0, retry_count=5)
```

---

## 3. 同步客户端 WjxtClient

### 3.1 生命周期

推荐使用 `with` 语句自动管理连接：

```python
from gxu_wjxt import WjxtClient

with WjxtClient(username="学号", password="密码") as client:
    client.login()
    # ... 使用客户端 ...
    client.logout()
# 退出 with 块后自动调用 close()
```

手动管理：

```python
client = WjxtClient(username="学号", password="密码")
try:
    client.login()
    # ... 使用客户端 ...
finally:
    client.logout()
    client.close()
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `client.base_url` | `str` | 系统根地址（如 `https://wjxt.gxu.edu.cn`） |
| `client.wjxt_ui` | `str` | 主应用路径（`{base_url}/Wjxt_UI`） |
| `client.logged_in` | `bool` | 是否已登录 |

### 3.2 认证

```python
# 登录 — 返回 True/False
success = client.login()
if not success:
    print("登录失败")

# 退出
client.logout()
```

登录成功后会维持 `ASP.NET_SessionId` Cookie，后续请求自动携带。SDK 默认启用 `auto_relogin`，会话过期时自动重新登录并重试请求（最多一次），对调用方完全透明。可通过 `WjxtConfig(auto_relogin=False)` 禁用，此时会抛出 `SessionExpiredError`。

### 3.3 部门列表

```python
# 获取所有部门
depts = client.get_departments()
for d in depts:
    print(f"ID: {d.id:>4}  名称: {d.tn_decoded}  类型: {d.type}")
```

每个部门是一个 `DepartmentInfo` 对象：

```python
@dataclass
class DepartmentInfo:
    id: int           # 部门 ID（如 16 表示学工部）
    type: int = 0     # 部门类型
    tn_encoded: str   # GB2312 URL 编码后的名称
    tn_decoded: str   # 解码后的可读名称
    url: str          # 该部门文件列表的完整 URL
```

常用部门 ID 速查：

| ID | 部门 |
|----|------|
| 16 | 学工部（处）、武装部（就业中心） |
| 22 | 教务处（教师发展中心） |
| 24 | 研究生院 |
| 47 | 计电学院 |
| 90 | 校团委 |
| 196 | 人工智能学院 |

> 完整列表见 [api.md](api.md) 第八节。

### 3.4 文件列表与遍历

#### 单页获取

```python
# 获取全部文件第 1 页，同时返回文件列表和分页信息
files, page_info = client.get_file_list_structured(page=1)
print(f"第 {page_info.current_page}/{page_info.total_pages} 页")
print(f"每页 {page_info.per_page} 条，共 {page_info.total_items} 条")

for f in files:
    print(f"[{f.index}] {f.department}: {f.title} ({f.date})")
    print(f"  ID: {f.id}, 未读: {f.is_unread}")
```

`PaginationInfo` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `current_page` | `int` | 当前页码 |
| `total_pages` | `int` | 总页数 |
| `per_page` | `int` | 每页条数（固定 50） |
| `total_items` | `int` | 符合条件的总条数 |

#### 惰性遍历（自动翻页）

```python
# 遍历全部文件，自动翻页
for f in client.iter_files(max_pages=10):
    print(f"[{f.index}] {f.department}: {f.title}")

# 遍历指定部门的文件
for f in client.iter_dept_files(dept_id=16, dept_name="学工部", max_pages=5):
    print(f"[{f.index}] {f.title}")
```

- `max_pages=None` 表示遍历所有页
- 每页之间自动间隔 `page_delay` 秒（默认 0.5）
- 返回的是 `Iterator[FileInfo]`，惰性加载，内存友好

#### 部门文件列表

```python
# 获取原始 HTML
html = client.get_dept_files(dept_id=16, dept_name="学工部", page=1)

# 获取结构化数据
files, page_info = client.get_file_list_structured(page=1)
```

#### 低级 API

```python
# 获取全部文件页面的原始 HTML
html = client.get_all_files()

# 获取带翻页参数的原始 HTML
html = client.get_file_list(list_id=127, list_type=100, list_name="全部文件", page=3)

# 获取部门文件的原始 HTML
html = client.get_dept_files(dept_id=16, dept_name="学工部", page=2)
```

`FileInfo` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int \| None` | 文件 ID |
| `index` | `str` | 列表中序号 |
| `title` | `str` | 文件标题 |
| `department` | `str` | 发布部门名称 |
| `date` | `str` | 发布日期（`YYYY-MM-DD`） |
| `is_unread` | `bool` | 是否未读 |
| `detail_url` | `str` | 详情页完整 URL |

### 3.5 文件详情与下载

#### 获取详情

```python
detail = client.get_file_detail(file_id=61424)

print(f"标题: {detail.title}")
print(f"正文长度: {len(detail.raw_html)} 字符")
print(f"附件数: {len(detail.download_urls)}")

for att in detail.download_urls:
    print(f"  - {att.filename}: {att.url}")
```

`FileDetail` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `file_id` | `int` | 文件 ID |
| `title` | `str` | 文件标题 |
| `detail_url` | `str` | 详情页 URL |
| `raw_html` | `str` | 正文 HTML 源码 |
| `download_urls` | `list[Attachment]` | 附件列表 |

`Attachment` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | `str` | 下载链接（相对路径以 `/` 开头） |
| `filename` | `str` | 原始文件名 |

#### 下载文件

```python
# 通过文件 ID 下载
path = client.download_file(file_id=61424, save_dir="./downloads")
if path:
    print(f"已下载到: {path}")

# 通过 URL 直接下载
path = client.download_file(
    url="/filezip/uploadfile/2026/05/somefile.xlsx",
    save_dir="./downloads"
)
```

`download_file` 返回保存路径（`str`），失败返回 `None`。

### 3.6 搜索

```python
from gxu_wjxt import SearchParams

# 标题搜索
result = client.search(keyword="奖学金", search_type="title")
print(f"搜索到 {result.total_count} 条, {result.total_pages} 页")
for f in result.files[:5]:
    print(f"  [{f.index}] {f.department}: {f.title} ({f.date})")

# 全文搜索
result = client.search(keyword="奖学金", search_type="content")

# 文件号搜索
result = client.search(keyword="2026", search_type="fileNum")

# 组合筛选
result = client.search(
    keyword="通知", search_type="title",
    file_year="2026",           # 年份
    file_type="16",             # 学工部
    match_mode="Fuzzy",         # 模糊匹配
)

# SearchParams 对象
params = SearchParams(keyword="考试", file_year="2026")
result = client.search(params, page=2)  # 翻页

# 惰性遍历搜索结果（自动翻页）
for f in client.iter_search(keyword="2026", max_pages=3):
    print(f.title)

# 向后兼容接口（仍可用）
result = client.search_files(keyword="奖学金")
result = client.file_search(keyword="奖学金")
```

**搜索参数 (`SearchParams`):**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | str | `""` | 搜索关键词 |
| `search_type` | str | `"title"` | `"title"` / `"fileNum"` / `"content"` |
| `file_type` | str | `"全部文件"` | `"全部文件"` / `"前一周文件"` / `"前一个月文件"` / 部门 ID |
| `file_year` | str | `"0"` | `"0"` = 全部年份, 或 `"2026"` 等 |
| `match_mode` | str | `"Fuzzy"` | `"Fuzzy"` 模糊 / `"Accurate"` 精确 |

**返回 (`SearchResult`):**

| 字段 | 类型 | 说明 |
|------|------|------|
| `files` | `list[FileInfo]` | 当前页文件列表 |
| `total_count` | int | 搜索结果总数 |
| `current_page` | int | 当前页码 |
| `total_pages` | int | 总页数 |
| `per_page` | int | 每页条数（固定 50） |

### 3.7 电话簿

```python
# 获取并解析电话簿
contacts = client.parse_phone_list()
for c in contacts:
    print(f"{c.name}: {c.phone}")

# 分步操作
html = client.get_phone_list()
contacts = client.parse_phone_list(html)
```

`PhoneContact` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 联系人姓名 |
| `phone` | `str` | 电话号码 |
| `extra` | `str` | 附加信息（`\|` 分隔） |

### 3.8 密码修改

```python
success = client.change_password(
    old_password="old_password",
    new_password="NewPwd@123"
)
```

> **密码要求：** 必须包含大写字母、小写字母、数字、特殊字符，长度 8-30 位。

### 3.9 业务办理

```python
# 各业务页面均返回 BusinessPage 结构
for label, page in [
    ("待办事项", client.get_todo_list()),
    ("已批申请", client.get_todo_processing()),
    ("全部申请", client.get_my_update_lists()),
]:
    print(f"{label}: 标签=\"{page.active_tab}\", "
          f"导航={list(page.nav_links.keys())}, "
          f"搜索={'有' if page.has_search else '无'}, "
          f"记录={len(page.records)}条")

# BusinessPage 字段参考:
#   page_type    — 页面标识: "mytodolists"/"do_list"/"my_todo_lists"/"my_up_lists"/"add"
#   active_tab   — 当前激活的导航标签
#   nav_links    — 标签名 → URL 映射
#   records      — list[BusinessRecord] (无数据时为空)
#   total_count  — GridView 总记录数 (0 = 无数据或不可见)
#   has_search   — 是否有搜索框 (仅 business_DoList.aspx)
#   raw_html     — 原始 HTML

# 获取新建业务表单（只读查看表单结构）
page = client.get_business_add_page()
print(f"表单页面 {len(page.raw_html)} 字节")

# 提交新业务（⚠️ 会创建真实业务工单，谨慎使用）
# response = client.add_business({
    "field_name": "value",
    # ... 更多表单字段 ...
})
```

---

## 4. 异步客户端 AsyncWjxtClient

异步客户端与同步客户端 API 完全一致，区别在于：

- 所有方法都是 `async`，需要 `await`
- 迭代器返回 `AsyncIterator[FileInfo]`
- 翻页延迟使用 `asyncio.sleep()`
- 使用 `async with` 管理生命周期

### 基本用法

```python
import asyncio
from gxu_wjxt import AsyncWjxtClient

async def main():
    async with AsyncWjxtClient(username="学号", password="密码") as client:
        await client.login()

        # 获取部门列表
        depts = await client.get_departments()
        for d in depts:
            print(f"[{d.id}] {d.tn_decoded}")

        # 惰性遍历文件
        async for f in client.iter_files(max_pages=3):
            print(f"[{f.index}] {f.title}")

        # 获取文件详情
        detail = await client.get_file_detail(file_id=61424)
        print(f"标题: {detail.title}")

        # 下载文件
        path = await client.download_file(file_id=61424, save_dir="./downloads")

        await client.logout()

asyncio.run(main())
```

### 并发遍历多个部门

```python
import asyncio
from gxu_wjxt import AsyncWjxtClient

async def fetch_dept_files(client, dept_id, dept_name):
    """获取单个部门的前 3 页文件"""
    files = []
    async for f in client.iter_dept_files(dept_id, dept_name, max_pages=3):
        files.append(f)
    return dept_name, files

async def main():
    async with AsyncWjxtClient(username="学号", password="密码") as client:
        await client.login()

        depts = await client.get_departments()
        # 并发获取多个部门的文件
        tasks = [
            fetch_dept_files(client, d.id, d.tn_decoded)
            for d in depts[:5]
        ]
        results = await asyncio.gather(*tasks)

        for name, files in results:
            print(f"{name}: {len(files)} 个文件")

asyncio.run(main())
```

> **注意：** 虽然可以并发遍历部门，但底层共享同一个 HTTP 客户端，实际并发度受 httpx 连接池限制。大量并发时注意对服务器的压力。

---

## 5. 文件爬虫 FileCrawler

`FileCrawler` 是高层封装，提供批量下载、过滤、多线程、下载记录等功能。

### 5.1 基本用法

```python
from gxu_wjxt import WjxtClient, FileCrawler

with WjxtClient(username="学号", password="密码") as client:
    client.login()

    crawler = FileCrawler(
        client=client,
        download_dir="./downloads",  # 下载目录
        workers=8,                    # 并发线程数
        page_delay=0.5,              # 翻页间隔（秒）
    )

    stats = crawler.crawl_all(unread_only=True)
    print(f"下载: {stats.downloaded}, 跳过: {stats.skipped}")
```

### 5.2 爬取策略

三种策略覆盖不同使用场景：

#### crawl_all — 全部文件（不分部门）

```python
stats = crawler.crawl_all(
    max_pages=10,           # 最多翻 10 页（None = 全部）
    after=date(2026, 3, 1), # 只下载此日期之后的文件
    unread_only=True,       # 只下载未读文件
    dry_run=False,          # True = 预览模式，不实际下载
    max_empty_pages=3,      # 连续 3 页无匹配则停止（0 = 禁用）
)
```

#### crawl_department — 指定部门

```python
stats = crawler.crawl_department(
    dept_id=16,
    dept_name="学工部（处）、武装部（就业中心）",
    max_pages=5,
    unread_only=True,
    max_empty_pages=3,
)
```

#### crawl_all_departments — 遍历所有部门

```python
stats = crawler.crawl_all_departments(
    max_pages=3,       # 每个部门最多翻 3 页
    unread_only=True,
    max_empty_pages=3,
)
```

遍历所有部门时，某个部门出错不会中断整体流程（错误会被打印并跳过）。

### 5.3 过滤与提前停止

#### 过滤参数

- **`unread_only=True`**：只下载标记为"未读"的文件。文件列表中红色 `[未读]` 标记对应 `FileInfo.is_unread == True`
- **`after=date(2026, 3, 1)`**：只下载该日期（含）之后的文件。日期字符串格式为 `YYYY-MM-DD`

两者可组合使用：

```python
# 只下载 3 月 1 日之后且未读的文件
stats = crawler.crawl_all(after=date(2026, 3, 1), unread_only=True)
```

#### 提前停止 (max_empty_pages)

翻页过程中，如果连续 N 页没有任何文件满足过滤条件，爬虫会自动停止。这在 `unread_only=True` 时特别有用——当已读文件集中在较新页面，翻到旧页面可能全是已读，无需继续。

```python
# 默认：连续 3 页无匹配即停止
crawler.crawl_all(unread_only=True)

# 连续 5 页无匹配才停止
crawler.crawl_all(unread_only=True, max_empty_pages=5)

# 禁用提前停止，翻完所有页
crawler.crawl_all(unread_only=True, max_empty_pages=0)
```

> **原理：** 文件列表按时间倒序排列（最新在前）。`unread_only=True` 时，未读文件大概率集中在前几页。一旦翻到全是已读的页面，继续翻旧页大概率也是已读。`max_empty_pages` 在效率和不遗漏之间取平衡。

### 5.4 多线程下载

```python
crawler = FileCrawler(client, download_dir="./downloads", workers=8)
```

- `workers=1`（默认）：串行下载，显示进度条
- `workers > 1`：使用 `ThreadPoolExecutor` 并发下载，线程安全

进度条示例：

```
  [████████████░░░░░░░░] 8/10  80%
```

> **注意：** 多线程下载时，如果网站限制了单个 IP 的并发连接数，过高的 `workers` 可能导致部分请求失败。建议从 3-5 开始尝试。

### 5.5 下载记录与断点续爬

爬虫在下载目录自动维护 `download_history.json`：

```json
{
    "updated": "2026-05-19T10:30:00",
    "count": 42,
    "downloaded": [
        "abc123def456...",
        "789ghi012jkl..."
    ]
}
```

- 每个文件通过 `md5("wjxt_file_{file_id}")` 生成唯一哈希
- 已下载的文件在后续运行中自动跳过（`stats.skipped` 计数）
- 调用 `crawler.clear_history()` 可清除记录重新下载

```python
# 清除下载记录
crawler.clear_history()

# 查看已下载列表
print(f"已下载 {len(crawler.history)} 个文件")
```

### 5.6 输出目录结构

```
downloads/
├── download_history.json
├── 学工部（处）、武装部（就业中心）/
│   ├── 2026-05-16_关于xxx通报/
│   │   ├── 2026-05-16_关于xxx通报.html    ← 文件正文
│   │   ├── 附件1.doc
│   │   └── 附件2.xlsx
│   └── 2026-05-15_关于yyy通知/
│       └── ...
├── 校团委/
│   └── ...
└── 广西大学/                               ← 未知部门文件的默认目录
    └── ...
```

- 第一层：部门名称（经过安全文件名处理）
- 第二层：`{日期}_{标题}/`（截断到 100 字符）
- 第三层：正文 HTML + 所有附件

---

## 6. 数据类参考

### PaginationInfo

```python
@dataclass
class PaginationInfo:
    current_page: int = 1    # 当前页码
    total_pages: int = 1     # 总页数
    per_page: int = 50       # 每页条目数
    total_items: int = 0     # 符合条件的总条目数
```

### FileInfo

```python
@dataclass
class FileInfo:
    id: Optional[int]         # 文件 ID（部分行可能为 None）
    index: str = ""           # 序号（如 "[1]"）
    title: str = ""           # 标题
    department: str = ""      # 发布部门
    date: str = ""            # 日期（YYYY-MM-DD）
    is_unread: bool = False   # 是否有 [未读] 标记
    detail_url: str = ""      # 详情页完整 URL
```

### FileDetail

```python
@dataclass
class FileDetail:
    file_id: int                      # 文件 ID
    title: str = ""                   # 标题
    detail_url: str = ""              # 详情页 URL
    raw_html: str = ""                # 正文 HTML
    download_urls: list[Attachment]   # 附件列表

    @property
    def download_url(self) -> str:    # 第一个附件的 URL，无附件返回 ""
```

### Attachment

```python
@dataclass
class Attachment:
    url: str        # 下载 URL
    filename: str   # 原始文件名
```

### DepartmentInfo

```python
@dataclass
class DepartmentInfo:
    id: int           # 部门 ID
    type: int = 0     # 部门类型
    tn_encoded: str   # GB2312 编码的名称
    tn_decoded: str   # 解码后的名称
    url: str          # 该部门文件列表的 URL
```

### PhoneContact

```python
@dataclass
class PhoneContact:
    name: str = ""    # 姓名
    phone: str = ""   # 电话号码
    extra: str = ""   # 附加信息（" | " 连接的多值）
```

### CrawlStats

```python
@dataclass
class CrawlStats:
    total_files: int = 0     # 扫描的文件总数
    downloaded: int = 0      # 本次新下载的文件数
    skipped: int = 0         # 已在历史记录中跳过的文件数
    no_attachment: int = 0   # 无附件（仅正文 HTML）的文件数
    failed: int = 0          # 下载失败的文件数
```

所有 `inc_*` 方法（`inc_downloaded()`、`inc_skipped()` 等）都是线程安全的。

---

## 7. 异常处理

```python
from gxu_wjxt import (
    WjxtError, AuthError, NetworkError, ParseError,
    SessionExpiredError, DownloadError,
)

try:
    client.login()
    files, _ = client.get_file_list_structured(page=1)
except AuthError:
    print("认证失败：用户名或密码错误")
except SessionExpiredError:
    print("会话过期：需要重新登录")
except NetworkError:
    print("网络错误：无法连接到服务器")
except ParseError:
    print("解析错误：页面结构可能发生了变化")
except DownloadError:
    print("下载失败：文件不存在或权限不足")
except WjxtError as e:
    print(f"SDK 错误: {e}")
```

异常层次结构：

```
Exception
└── WjxtError
    ├── AuthError           # 登录失败
    ├── NetworkError        # 网络请求失败
    ├── ParseError          # HTML 解析失败
    ├── SessionExpiredError # 会话过期
    └── DownloadError       # 文件下载失败
```

### 常见异常场景及处理

> 会话过期自动重连默认已启用，通常无需手动处理 `SessionExpiredError`。以下示例适用于 `auto_relogin=False` 或需要自定义重试逻辑的场景。

```python
from gxu_wjxt import WjxtClient, FileCrawler, WjxtConfig, SessionExpiredError, NetworkError
import time

# 方式 A：默认自动重连（推荐，大多数场景无需额外代码）
def crawl_simple(username, password):
    with WjxtClient(username=username, password=password) as client:
        client.login()
        crawler = FileCrawler(client, workers=4)
        return crawler.crawl_all(unread_only=True, max_empty_pages=5)

# 方式 B：禁用自动重连，手动处理
def crawl_with_manual_retry(username, password, max_retries=3):
    config = WjxtConfig(auto_relogin=False)
    for attempt in range(max_retries):
        try:
            with WjxtClient(username=username, password=password, config=config) as client:
                if not client.login():
                    print("登录失败")
                    return None
                crawler = FileCrawler(client, workers=4)
                return crawler.crawl_all(unread_only=True, max_empty_pages=5)

        except SessionExpiredError:
            print(f"会话过期，第 {attempt + 1} 次重试...")
            time.sleep(2)

        except NetworkError as e:
            print(f"网络错误: {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise

    return None
```

---

## 8. CLI 命令行

```bash
# 基本用法
gxu-wjxt -u 学号 -p 密码 -o ./downloads

# 仅下载未读文件
gxu-wjxt -u 学号 -p 密码 --unread-only

# 指定部门 + 限制页数
gxu-wjxt -u 学号 -p 密码 -d 16 -n 5

# 所有部门
gxu-wjxt -u 学号 -p 密码 -d all -n 3

# 多线程 + 预览
gxu-wjxt -u 学号 -p 密码 --workers 8 --dry-run

# 日期过滤
gxu-wjxt -u 学号 -p 密码 --after 2026-03-01

# 调整空页停止阈值
gxu-wjxt -u 学号 -p 密码 --unread-only --max-empty-pages 5

# 兼容旧版 crawler.py 入口
python -m gxu_wjxt.cli -o ./downloads --after 2026-03-01
```

完整参数列表：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-o, --output` | `str` | `./downloads` | 下载目录 |
| `-d, --dept` | `str` | `None` | 部门 ID 或 `all`（`None` = 不按部门分组） |
| `-n, --max-pages` | `int` | `None` | 每个部门/列表最大页数 |
| `--after` | `str` | `None` | 日期过滤（`YYYY-MM-DD`） |
| `--unread-only` | flag | `False` | 仅下载未读文件 |
| `--workers` | `int` | `1` | 并发线程数 |
| `--max-empty-pages` | `int` | `3` | 连续多少页无匹配时停止（`0` = 禁用） |
| `--dry-run` | flag | `False` | 预览模式 |
| `-u, --username` | `str` | `None` | 用户名 |
| `-p, --password` | `str` | `None` | 密码 |

凭证不通过命令行提供时，CLI 会依次尝试环境变量 → `./config.json` → `~/.gxu_wjxt.json`。

---

## 9. 最佳实践

### 使用 with 语句

```python
# 推荐：自动清理连接
with WjxtClient(username="学号", password="密码") as client:
    client.login()
    # ...

# 异步同理
async with AsyncWjxtClient(username="学号", password="密码") as client:
    await client.login()
    # ...
```

### 注意翻页间隔

系统每页 50 条记录，翻页过于频繁可能被服务器限制。默认 `page_delay=0.5` 秒，如需加速请适度调整。

### 善用过滤减少请求

```python
# 差：翻完 295 页找 3 个未读文件
crawler.crawl_all(unread_only=True, max_empty_pages=0)

# 好：发现连续 3 页无未读就停
crawler.crawl_all(unread_only=True, max_empty_pages=3)

# 更好：加日期过滤缩小范围
crawler.crawl_all(
    after=date(2026, 5, 1),
    unread_only=True,
    max_empty_pages=3,
)
```

### 断点续爬

`download_history.json` 确保重复运行不会重复下载。定期爬取时无需手动管理：

```python
# 每周运行一次，只下载本周新发布的未读文件
from datetime import date, timedelta

last_week = date.today() - timedelta(days=7)
stats = crawler.crawl_all(after=last_week, unread_only=True)
```

### 先预览再下载

```python
# 第一步：预览
crawler.crawl_all(unread_only=True, dry_run=True)

# 确认无误后再实际下载
crawler.crawl_all(unread_only=True, dry_run=False)
```

### 按部门分批下载

当文件量很大时，按部门逐一下载比一次性爬全部更可控：

```python
depts = client.get_departments()
for d in depts:
    if d.id in (16, 22, 24):  # 只下载特定部门
        print(f"\n处理部门: {d.tn_decoded}")
        stats = crawler.crawl_department(
            d.id, d.tn_decoded,
            max_pages=5,
            unread_only=True,
        )
        print(f"  {stats.downloaded} 个新文件")
```

### 处理中断

爬虫支持 `Ctrl+C` 安全中断。中断时已完成下载的文件会被记录到 `download_history.json`，下次运行自动跳过：

```python
try:
    stats = crawler.crawl_all(unread_only=True)
except KeyboardInterrupt:
    print("\n已中断。下载记录已保存，下次运行将从断点继续。")
```

> CLI 模式同样支持安全中断。
