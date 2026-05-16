# 广西大学文件管理系统 Python 客户端

[wjxt.gxu.edu.cn](https://wjxt.gxu.edu.cn) 的 Python 爬虫工具集，提供 API 封装、文件下载、数据解析。

## 项目结构

```
.
├── client.py              # API 客户端（核心库）
├── crawler.py             # 文件下载爬虫
├── demo.py                # 功能演示脚本
├── api.md                 # API 接口文档
├── config.example.json    # 配置文件模板
├── config.json            # 配置文件（已 gitignore）
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install requests beautifulsoup4
```

### 2. 配置账密

```bash
cp config.example.json config.json
# 编辑 config.json，填入你的学号和密码
```

`config.json` 格式：

```json
{
    "username": "your_student_id",
    "password": "your_password"
}
```

### 3. 运行演示

```bash
python demo.py
```

## 使用方式

### client.py — API 客户端

```python
from client import WjxtClient

client = WjxtClient("学号", "密码")
client.login()

# 获取部门列表
depts = client.get_departments()

# 获取文件列表（分页）
html = client.get_file_list(page=1)
files = client.parse_file_list(html)
info = client.get_pagination_info(html)

# 获取文件详情与下载链接
detail = client.get_file_detail(file_id=61424)
# detail["download_urls"] -> [{url, filename}, ...]

# 下载文件
client.download_file(file_id=61424, save_dir="./downloads")

# 获取电话簿
contacts = client.parse_phone_list()

client.logout()
```

### crawler.py — 文件下载爬虫

```bash
# 下载全部文件
python crawler.py -o ./downloads

# 只下载某个部门最近 3 页
python crawler.py -d 16 -n 3

# 遍历所有部门
python crawler.py -d all

# 仅下载指定日期之后的文件
python crawler.py --after 2026-03-01

# 仅下载未读文件
python crawler.py --unread-only

# 预览模式（不实际下载）
python crawler.py --dry-run

# 指定输出目录
python crawler.py -o /path/to/dir
```

#### 参数说明

| 参数 | 说明 |
|------|------|
| `-o, --output` | 下载目录（默认 `./downloads`） |
| `-d, --dept` | 部门 ID 或 `all`（默认全部文件不分部门） |
| `-n, --max-pages` | 每个部门最多爬取页数 |
| `--after` | 日期过滤 `YYYY-MM-DD` |
| `--unread-only` | 仅下载未读文件 |
| `--workers` | 并发线程数（默认 1） |
| `--dry-run` | 预览模式 |
| `-u, --username` | 用户名（覆盖配置文件） |
| `-p, --password` | 密码（覆盖配置文件） |

#### 输出目录结构

```
downloads/
├── download_history.json          # 下载记录（断点续爬）
├── 学工部（处）、武装部（就业中心）/
│   └── 2026-05-16_关于xxx通报/
│       ├── 2026-05-16_关于xxx通报.html    # 文件正文
│       ├── 附件1.doc                       # 附件
│       └── 附件2.xlsx                      # 附件
└── 校团委/
    └── ...
```

### demo.py — 演示脚本

```bash
python demo.py
```

依次演示：登录 → 主页 → 文件列表 → 部门文件 → 文件下载 → 电话簿 → 业务办理 → 退出。

## API 接口

共 19 个端点，覆盖认证、文件管理、搜索、用户、电话簿、业务办理。详见 [api.md](api.md)。

| 模块 | 关键端点 |
|------|----------|
| 认证 | `default.aspx` `Login.aspx` |
| 主页 | `Wjxt_UI/default.aspx` `WebUI.aspx` |
| 文件管理 | `PageList.aspx` `qstwj.aspx` `showfile.aspx` |
| 文件下载 | `/filezip/uploadfile/{year}/{month}/{filename}` |
| 搜索 | `search.aspx` `filesearch.aspx` |
| 用户 | `userEditPss.aspx` `Exiting.aspx` |
| 电话簿 | `phoneList.aspx` |
| 业务 | `business/business_*.aspx` |

## 依赖

- Python 3.10+
- [requests](https://pypi.org/project/requests/) — HTTP 请求
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) — HTML 解析

## 注意事项

- 搜索功能当前返回"系统维护中"，非代码问题
- 大量文件列表中约 50% 为纯文本公告，无附件可下载，属正常现象
- 默认 0.5 秒翻页间隔，避免对服务器造成压力
- `config.json` 包含敏感信息，已加入 `.gitignore`
