# 广西大学文件管理系统 API 文档

> 网站: `https://wjxt.gxu.edu.cn`
> 框架: ASP.NET Web Forms (IIS 7.5 / ASP.NET 4.0)
> 编码: GB2312 / UTF-8 (混合)

---

## 通用说明

### 认证机制

系统使用 `ASP.NET_SessionId` Cookie 维持登录状态。所有 API 请求（除登录外）需要携带该 Cookie。

### 请求格式

- Content-Type: `application/x-www-form-urlencoded`
- 页面编码: 主要为 `gb2312`，部分业务页面为 `utf-8`
- 所有 POST 请求必须携带 `__VIEWSTATE` 和 `__VIEWSTATEGENERATOR` 字段

### VIEWSTATE 机制

ASP.NET Web Forms 使用 VIEWSTATE 维护页面状态。每次 GET 页面后，需要从 HTML 中提取 `__VIEWSTATE` 值，在 POST 请求中原样返回。翻页通过设置 `__EVENTTARGET=AspNetPager1` 和 `__EVENTARGUMENT=<页码>` 实现。

---

## 一、认证模块

### 1.1 登录页面

```
GET /Login.aspx
GET /default.aspx
```

**响应:** 登录表单 HTML，包含 VIEWSTATE 隐藏字段。

**表单字段:**

| 字段名 | 说明 |
|--------|------|
| `__VIEWSTATE` | ASP.NET 视图状态（从页面提取） |
| `__VIEWSTATEGENERATOR` | 视图状态生成器标识 |
| `__SCROLLPOSITIONX` | 滚动位置 X，固定为 `0` |
| `__SCROLLPOSITIONY` | 滚动位置 Y，固定为 `0` |
| `__EVENTTARGET` | 事件目标，固定为空 |
| `__EVENTARGUMENT` | 事件参数，固定为空 |
| `userIdCard` | 用户名/学号 |
| `userPwd` | 密码 |
| `loginsubmit` | 提交按钮，值为 `登 录` |
| `myteip` | 客户端 IP 标记 |

### 1.2 登录提交

```
POST /default.aspx
Content-Type: application/x-www-form-urlencoded
```

**参数:** 同登录页面表单字段。

**成功响应:** 页面包含 JavaScript 重定向 `window.open('Wjxt_UI/default.aspx', ...)`。

### 1.3 退出登录

```
GET /Wjxt_UI/Exiting.aspx
```

---

## 二、主应用模块

### 2.1 主应用框架

```
GET /Wjxt_UI/default.aspx
```

**说明:** 主应用外壳页面，包含 iframe 布局结构。

**内部 iframe:**
- `WebUI.aspx?id=2` — 左侧导航栏
- `WebUI.aspx?id=4` — 主内容区（部门列表）
- `qstwj.aspx` — 文件列表

### 2.2 左侧导航栏

```
GET /Wjxt_UI/WebUI.aspx?id=2
```

**说明:** 包含搜索表单和快捷操作链接。引用 `filesearch.aspx` 用于文件检索。

### 2.3 部门列表

```
GET /Wjxt_UI/WebUI.aspx?id=4
```

**说明:** 显示所有部门分类，每个部门链接到 `Right.aspx`。

---

## 三、文件管理模块

### 3.1 全部文件列表

```
GET /Wjxt_UI/qstwj.aspx
```

**说明:** 全量文件列表页面（约 1MB），显示所有未读文件。

**响应数据结构 (GridFiles 表格):**

| 列 | 说明 |
|----|------|
| 序号 | 文件索引 `[N]` |
| 部门:标题 | 格式: `<b>部门名</b>:<a href=showfile.aspx?id=N>标题</a>` |
| 未读标记 | `[未读]` 红色标记 |
| 日期 | 格式: `(YYYY年MM月DD日)` |

### 3.2 分页文件列表

```
GET /Wjxt_UI/PageList.aspx?id={list_id}&type={list_type}&tn={list_name}
POST /Wjxt_UI/PageList.aspx?id={list_id}&type={list_type}&tn={list_name}
```

**查询参数:**

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | int | 列表 ID | `127` |
| `type` | int | 列表类型 | `100` (全部文件) |
| `tn` | string | 列表名称 (GB2312 URL 编码) | `%C8%AB%B2%BF%CE%C4%BC%FE` (全部文件) |

**翻页:** POST 请求，设置 `__EVENTTARGET=AspNetPager1`，`__EVENTARGUMENT=<页码>`。

**分页信息格式:** `第N页/总M页  每页50条/共X条`

### 3.3 部门文件列表

```
GET /Wjxt_UI/Right.aspx?id={dept_id}&type={type}&tn={dept_name}
POST /Wjxt_UI/Right.aspx?id={dept_id}&type={type}&tn={dept_name}
```

**查询参数:**

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | int | 部门 ID | `16` (学工部) |
| `type` | int | 类型 | `0` |
| `tn` | string | 部门名称 (GB2312 URL 编码) | `%D1%A7%B9%A4%B2%BF` |

**翻页:** 同 PageList.aspx 方式。

### 3.4 文件详情

```
GET /Wjxt_UI/showfile.aspx?id={file_id}
```

**查询参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | int | 文件 ID |

**响应:** 文件详情页 HTML，包含:
- `document.title` — 文件标题
- `href="/filezip/uploadfile/{year}/{month}/{filename}"` — 文件下载链接

### 3.5 文件下载

```
GET /filezip/uploadfile/{year}/{month}/{filename}
```

**说明:** 实际文件下载端点。

**URL 示例:** `/filezip/uploadfile/2026/05/2026051620322323558.xlsx`

---

## 四、搜索模块

### 4.1 搜索页

```
GET /Wjxt_UI/search.aspx
```

**状态:** 当前返回"系统维护中"（可能于非工作时间禁用）。

### 4.2 文件高级搜索

```
GET /Wjxt_UI/filesearch.aspx
```

**状态:** 当前返回"系统维护中"（可能于非工作时间禁用）。

---

## 五、用户管理模块

### 5.1 修改密码页面

```
GET /Wjxt_UI/userEditPss.aspx
```

**表单字段:**

| 字段名 | 说明 |
|--------|------|
| `userName` | 用户名（自动填充） |
| `oldPwd` | 旧密码 |
| `userPWD1` | 新密码 |
| `userPWD2` | 确认新密码 |
| `BTN_initial_pwd` | 提交按钮 |

**密码要求:** 必须包含大写字母、小写字母、数字、特殊字符，长度 8-30 位。

### 5.2 提交密码修改

```
POST /Wjxt_UI/userEditPss.aspx
```

**参数:** 同修改密码页面表单字段 + VIEWSTATE 字段。

---

## 六、电话簿模块

### 6.1 内部电话簿

```
GET /Wjxt_UI/phoneList.aspx
```

**说明:** 显示内部联系人员电话列表，数据通过 ASP.NET GridView 渲染。

---

## 七、业务办理模块

所有业务页面位于 `/business/` 路径下。

### 7.1 待办列表

```
GET /business/business_mytodolists.aspx
```

### 7.2 待办处理

```
GET /business/business_DoList.aspx
```

**表单字段:** `TextBox1` (搜索框), `mysearch` (搜索按钮)。

### 7.3 我的待办列表

```
GET /business/business_MyToDoLists.aspx
```

### 7.4 我的更新列表

```
GET /business/business_MyUpLists.aspx
```

### 7.5 新增业务

```
GET /business/businessAdd.aspx
```

**说明:** 复杂的业务登记表单，包含多个区域（出差考察、培训、公务、会议、预决算、探亲、其他、附件等），约 70KB 的页面内容。

### 7.6 提交新业务

```
POST /business/businessAdd.aspx
```

**参数:** VIEWSTATE 字段 + 业务表单字段（字段因业务类型而异）。

---

## 八、部门 ID 参考

以下是部分常用部门的 ID 映射（完整列表参见 `Right.aspx` 页面）：

| ID | 部门名称 |
|----|----------|
| 5 | 211工程办公室 |
| 10 | 党办校办（督查办、法务办） |
| 11 | 行政文件 |
| 13 | 党委文件 |
| 14 | 驻校纪检监察组、校纪委 |
| 15 | 宣传部 |
| 16 | 学工部（处）、武装部（就业中心） |
| 17 | 保卫处（综治办） |
| 18 | 组织部（党校） |
| 19 | 校工会（校医院） |
| 20 | 计划生育委员会办公室 |
| 21 | 教工部、人资处 |
| 22 | 教务处（教师发展中心） |
| 23 | 科技处 |
| 24 | 研究生院 |
| 25 | 国合处（留服中心、港澳台办） |
| 26 | 发规处 |
| 27 | 对口支援工作办公室 |
| 29 | 财务处 |
| 30 | 国实处（招采中心） |
| 31 | 学生资助管理中心 |
| 32 | 招生就业指导中心 |
| 36 | 离退处 |
| 37 | 后勤基建处 |
| 38 | 档案馆 |
| 39 | 校友办 |
| 41 | 机械学院（实训中心） |
| 42 | 电气学院 |
| 43 | 土建学院 |
| 44 | 化工学院 |
| 45 | 资环材学院 |
| 46 | 轻工学院 |
| 47 | 计电学院 |
| 48 | 生科学院 |
| 49 | 农学院 |
| 50 | 林学院 |
| 51 | 动科学院 |
| 52 | 数学学院 |
| 53 | 物理学院 |
| 54 | 文学院 |
| 55 | 新闻学院 |
| 56 | 外语学院 |
| 57 | 公管学院 |
| 58 | 工商学院 |
| 59 | 法学院 |
| 63 | 马院 |
| 65 | 艺术学院 |
| 89 | 继教院 |
| 90 | 校团委 |
| 96 | 校庆办 |
| 106 | 国际学院 |
| 124 | 审计处 |
| 154 | 医学院 |
| 177 | 经济学院 |
| 187 | 科研院 |
| 196 | 人工智能学院 |

---

## 九、Python 客户端用法

```python
from client import WjxtClient

client = WjxtClient("username", "password")

# 登录
client.login()

# 获取部门列表
departments = client.get_departments()

# 获取文件列表 (分页)
html = client.get_file_list(page=1)
files = client.parse_file_list(html)
page_info = client.get_pagination_info(html)

# 获取文件详情
detail = client.get_file_detail(file_id=61424)
print(detail["title"], detail["download_url"])

# 下载文件
path = client.download_file(file_id=61424, save_dir="./downloads")

# 获取部门文件
html = client.get_dept_files(dept_id=16, dept_name="学工部（处）、武装部（就业中心）")
dept_files = client.parse_file_list(html)

# 获取所有文件 (自动翻页)
all_files = client.get_all_files_structured()

# 获取电话簿
contacts = client.parse_phone_list()

# 修改密码 (谨慎使用)
# client.change_password("old_password", "NewPwd@123")

# 退出
client.logout()
```
