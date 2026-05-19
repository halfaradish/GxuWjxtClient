# 广西大学文件系统 API 分析报告

> 目标站点: `https://wjxt.gxu.edu.cn`
> 分析时间: 2026-05-17
> 框架类型: ASP.NET Web Forms (IIS 7.5 / ASP.NET 4.0)

---

## 一、分析方法

### 1.1 信息收集流程

```
浏览器模拟 → 抓取登录页 → 解析表单结构 → 模拟登录 → 探索内页 → 提取接口
```

### 1.2 工具链

| 工具 | 用途 |
|------|------|
| `curl` | 初期 HTTP 探测、编码问题排查 |
| Python `requests` | 正式的会话管理与接口调用 |
| `BeautifulSoup4` | HTML 解析与数据提取 |
| `re` (正则) | VIEWSTATE 提取、下载链接匹配 |

### 1.3 分析步骤

1. 从登录页入手，分析 HTML 表单结构和隐藏字段
2. 使用 `requests.Session` 维持 Cookie，模拟登录
3. 登录成功后访问主应用框架，提取 iframe 引用
4. 递归探索每个 iframe 页面，收集 `.aspx` 链接
5. 对各页面进行深度分析：提取表单字段、`__doPostBack` 调用、数据表格结构
6. 验证翻页机制和文件下载流程

---

## 二、技术难点与解决方案

### 2.1 编码问题

**现象:** `curl` 下载的 HTML 内容显示为乱码。

**原因:** 服务器 `Content-Type` 声明 `charset=gb2312`，但部分页面实际使用 `utf-8`。

**尝试方案:**
- `curl` 的 `--data-urlencode` 会同时编码键名和键值，导致 `__VIEWSTATE` 被错误编码为 `%5F%5FVIEWSTATE`
- 使用 `iconv -f GBK -t UTF-8` 转码后阅读

**最终方案:** Python `requests` 库的 `resp.apparent_encoding` 自动检测编码，无需手动处理。

```python
# client.py 核心编码处理
resp.encoding = resp.apparent_encoding or "gb2312"
```

### 2.2 登录失败排查

**现象:** 多次尝试登录均返回"系统维护中，请稍后访问"。

**尝试方案:**
1. 直接 POST 到 `/default.aspx` → 302 重定向到错误页
2. 尝试 POST 到 `/Login.aspx` → 同样 302
3. 检查是否缺少隐藏字段、User-Agent 是否被拦截
4. 使用 Python 完整重放浏览器请求

**根因定位:** `curl` 的 `--data-urlencode` 对表单字段名也进行了 URL 编码，ASP.NET 无法识别。换成 Python `requests` 的 `data` 参数（不编码字段名）后解决。

**最终方案:**
```python
def login(self) -> bool:
    resp = self._get(f"{self.BASE_URL}/Login.aspx")
    fields = self._extract_viewstate(resp.text)
    fields["userIdCard"] = self.username
    fields["userPwd"] = self.password
    fields["loginsubmit"] = "登 录"
    fields["myteip"] = "172.28.222.133--2"
    resp2 = self._post(f"{self.BASE_URL}/default.aspx", data=fields)
    return "Wjxt_UI" in resp2.text
```

### 2.3 VIEWSTATE 与翻页机制

**现象:** 文件列表翻页需要 POST，但不能直接传页码参数。

**分析结果:** ASP.NET Web Forms 使用 `__doPostBack(eventTarget, eventArgument)` 实现分页。翻页需要：
1. 先从第一页 GET 请求中提取 `__VIEWSTATE`
2. POST 回同一 URL，设置 `__EVENTTARGET=AspNetPager1`、`__EVENTARGUMENT=<页码>`

**最终方案:**
```python
def get_file_list(self, page=1):
    if page <= 1:
        return self._get(base_url)
    resp1 = self._get(base_url)  # 获取 VIEWSTATE
    fields = self._extract_viewstate(resp1.text)
    fields["__EVENTTARGET"] = "AspNetPager1"
    fields["__EVENTARGUMENT"] = str(page)
    return self._post(base_url, data=fields)
```

### 2.4 多附件丢失问题

**现象:** `showfile.aspx?id=60983` 页面包含 2 个附件链接，但客户端只返回了第一个。

**根因:** `client.py` 的 `get_file_detail()` 使用 `re.search()` 只匹配第一个下载链接。

```python
# 错误代码
dl_m = re.search(r'href="(/filezip/uploadfile/[^"]+)"', resp.text)
```

**修复:** 改用 `re.finditer()` 遍历所有匹配项，同时提取 `download` 属性中的原始文件名。

```python
# 修复后
for m in re.finditer(
    r'<a[^>]*href="(/filezip/uploadfile/[^"]*)"[^>]*>',
    resp.text, re.I
):
    full_url = self.BASE_URL + m.group(1)
    dl_name = re.search(r'download="([^"]*)"', m.group(0))
    filename = dl_name.group(1) if dl_name else os.path.basename(m.group(1))
    attachments.append({"url": full_url, "filename": filename})
```

### 2.5 空文件夹问题

**现象:** 爬虫运行后输出目录出现大量空文件夹。

**根因:** `crawler.py` 的 `download_one()` 在确认文件有附件**之前**就执行了 `os.makedirs()`。

```python
# 错误顺序
os.makedirs(file_dir, exist_ok=True)   # 先创建
detail = client.get_file_detail(...)    # 再获取
if not attachments: return None         # 无附件时目录已空
```

**修复:** 将目录创建移到确认附件之后。

### 2.6 纯文本公告的处理策略演变

**第一版:** 无附件文件直接跳过 → 800 个文件仅下载 34 个

**第二版:** 无附件文件跳过但不创建空目录 → 优化了磁盘使用

**最终版:** 无附件文件也保存 HTML 正文到独立目录 → 100% 文件覆盖率

反馈：用户要求即使无附件也应保存 showfile.aspx 的 HTML 正文，因为这些页面本身就是完整文档。

### 2.7 隐私信息硬编码问题

**现象:** 用户名和密码以明文写死在 `crawler.py` 和 `demo.py` 中。

**修复:**
1. 创建 `config.json` 存放账密
2. 创建 `config.example.json` 作为提交到 git 的模板
3. `.gitignore` 排除 `config.json`
4. 两个脚本改用 `_load_config()` 加载，支持命令行参数覆盖
5. `--help` 不泄漏默认值（`default=None` + 运行时解析）

---

## 三、最终方案

### 3.1 项目产出

| 文件 | 说明 |
|------|------|
| `client.py` (616行) | API 客户端核心库，封装 19 个端点 |
| `crawler.py` (507行) | 文件下载爬虫，支持过滤/翻页/断点续爬 |
| `demo.py` (247行) | 10 个功能演示 |
| `api.md` (403行) | 完整 API 接口文档 |
| `config.example.json` | 配置文件模板 |
| `README.md` | 项目说明文档 |

### 3.2 发现的全部接口 (19个)

#### 认证模块
| 端点 | 方法 | 说明 |
|------|------|------|
| `/default.aspx` | GET/POST | 登录页面 / 登录提交 |
| `/Login.aspx` | GET | 登录页面 |
| `/Wjxt_UI/Exiting.aspx` | GET | 退出登录 |

#### 主页与导航
| 端点 | 方法 | 说明 |
|------|------|------|
| `/Wjxt_UI/default.aspx` | GET | 主应用框架 |
| `/Wjxt_UI/WebUI.aspx?id=2` | GET | 左侧导航/搜索 |
| `/Wjxt_UI/WebUI.aspx?id=4` | GET | 部门列表 |

#### 文件管理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/Wjxt_UI/qstwj.aspx` | GET | 全部文件列表 |
| `/Wjxt_UI/PageList.aspx` | GET/POST | 分页文件列表 |
| `/Wjxt_UI/Right.aspx` | GET/POST | 部门文件列表 |
| `/Wjxt_UI/showfile.aspx?id=N` | GET | 文件详情 (含附件链接) |
| `/filezip/uploadfile/{y}/{m}/{f}` | GET | 文件下载 |

#### 搜索
| 端点 | 方法 | 说明 |
|------|------|------|
| `/Wjxt_UI/search.aspx` | GET/POST | 文件搜索（需 GB2312 编码 POST） |
| `/Wjxt_UI/filesearch.aspx` | POST | 高级搜索（等同 search.aspx） |
| `/Wjxt_UI/showdoc.aspx?id=N` | GET | 搜索结果链接（等同 showfile.aspx） |

**搜索表单字段**（表单嵌入在侧边栏 `WebUI.aspx?id=2` 中）：

| 字段 | 值 | 说明 |
|------|------|------|
| `content` | 关键字 | 搜索关键词 |
| `searchType` | `title` / `fileNum` / `content` | 搜索类型：标题 / 文件号 / 全文 |
| `filetype` | `全部文件` 或部门 ID | 文件范围筛选 |
| `fileTime` | `0`（全部）或年份 | 年份筛选 |
| `AccurateFuzzy` | `Accurate` / `Fuzzy` | 精确 / 模糊匹配 |
| `__EVENTTARGET` | `Button1` | 触发搜索提交 |

**技术要点：**
- GET 请求返回"系统维护中"，必须用 POST 提交搜索
- **POST 数据必须 GB231K 编码**：中文关键字用 UTF-8 提交会导致"查无文件"
- `filesearch.aspx` 与 `search.aspx` 返回完全相同的搜索结果页
- 搜索结果链接为 `showdoc.aspx?id=N`，与 `showfile.aspx?id=N` 内容一致
- 搜索结果使用 `AspNetPager1` 分页（每页 50 条），翻页需用标准 UTF-8 POST

#### 用户管理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/Wjxt_UI/userEditPss.aspx` | GET/POST | 修改密码 |

#### 电话簿
| 端点 | 方法 | 说明 |
|------|------|------|
| `/Wjxt_UI/phoneList.aspx` | GET | 内部电话簿 |

#### 业务办理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/business/business_mytodolists.aspx` | GET | 待办列表 |
| `/business/business_DoList.aspx` | GET | 已批申请（含搜索框） |
| `/business/business_MyToDoLists.aspx` | GET | 我的待办列表 |
| `/business/business_MyUpLists.aspx` | GET | 全部申请（含 AspNetPager） |
| `/business/businessAdd.aspx` | GET/POST | 新增业务表单 / 提交 |

**页面结构:**
- 导航标签: 填写申请 \| 待办事项 \| 已批申请 \| 全部申请
- 数据渲染: `gvList1` GridView（ASP.NET AJAX，无数据时不可见）
- `businessAdd.aspx` 包含 7 种业务类型（出差、培训、公务、会议、预决算、探亲、其他）+ 附件区域

### 3.3 数据统计

- 部门总数: 95 个
- 全部文件总数: 14,715 条 (295 页 × 50 条/页)
- 附件率: 约 50% 的文件包含可下载附件
- 学工部文件: 2,428 条 (49 页)
- 电话簿联系人: 101 人

**搜索数据（2026-05-19 实测）：**

| 搜索类型 | 关键字 | 结果数 |
|---------|--------|--------|
| 标题模糊 | "关于" | 12,873 条 (258 页) |
| 全文模糊 | "奖学金" | 14,653 条 (294 页) |
| 文件号模糊 | "2026" | 7,667 条 (154 页) |
| 标题模糊 × 2025 年 | "通知" | 345 条 (7 页) |
| 标题模糊 × 学工部 | "学生" | 2,229 条 (45 页) |
| 标题模糊 × 2026 年 | "通知" | 138 条 (3 页) |

### 3.4 爬虫输出目录结构

```
downloads/
├── download_history.json          # 断点续爬记录
├── 学工部（处）、武装部（就业中心）/
│   ├── 2026-05-16_关于xxx通报/
│   │   ├── 2026-05-16_关于xxx通报.html   # 文件正文
│   │   ├── 附件1.xlsx                     # 附件
│   │   └── 附件2.docx                     # 附件
│   └── 2026-05-08_关于xxx决定/            # 纯公告（仅HTML）
│       └── 2026-05-08_关于xxx决定.html
└── 校团委/
    └── ...
```

---

## 四、经验总结

### 技术要点

1. **ASP.NET Web Forms 逆向:** 关键在于理解 VIEWSTATE 机制和 `__doPostBack` 分页模式
2. **编码处理:** 不要信任服务器声明的编码，使用 `apparent_encoding` 自动检测
3. **POST 数据编码陷阱:** ASP.NET 服务器端使用 GB2312 解码表单数据，中文关键字必须 GB2312 编码 POST 才能被正确识别；UTF-8 提交会返回"查无文件"
4. **curl vs requests:** curl 的 `--data-urlencode` 对字段名编码会导致表单提交失败，requests 的 `data=` 参数字段名不编码
5. **正则匹配:** `re.search()` 只返回首个匹配，多值场景必须用 `re.finditer()`
6. **会话过期检测:** 服务端返回 `<script>alert('登录信息安全时限过期，请重新登录！');window.parent.location.href='../default.aspx';</script>`（105 字节），通过检测"请重新登录"文本可区分正常登出（63 字节无 alert）
7. **业务办理模块分析:** 页面使用 ASP.NET AJAX (ScriptManager + UpdatePanel)，GridView `gvList1` 在有记录时才渲染数据行，无数据时完全隐藏。导航标签通过 `<strong>` 标记当前页。`business_DoList.aspx` 含搜索框 (`TextBox1`)。`businessAdd.aspx` 包含出差、培训、公务、会议、预决算、探亲、其他 7 种业务类型的表单区域。

### 文件组织建议

- 页面是"公告" — showfile.aspx 的 HTML 正文即文件内容
- 附件是"附属文件" — 嵌入在页面中的 Word/PDF/Excel 链接
- 两者都应保留，因为纯文本公告的正文就是 HTML 本身

### 局限性

- 业务办理模块仅完成只读分析（页面结构、导航标签、搜索表单），GridView 在有数据时才会渲染行，当前测试账号无业务记录，无法验证数据行解析
- `add_business()` 提交会创建真实业务工单，不建议自动化测试
