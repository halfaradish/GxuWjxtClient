# @gxuwjxt/node SDK 使用指南

> 广西大学文件管理系统 Node.js/TypeScript SDK 完整使用文档

---

## 目录

1. [安装](#1-安装)
2. [配置](#2-配置)
3. [客户端 WjxtClient](#3-客户端-wjxtclient)
   - [3.1 生命周期](#31-生命周期)
   - [3.2 认证](#32-认证)
   - [3.3 部门列表](#33-部门列表)
   - [3.4 文件列表与遍历](#34-文件列表与遍历)
   - [3.5 文件详情与下载](#35-文件详情与下载)
   - [3.6 搜索](#36-搜索)
   - [3.7 电话簿](#37-电话簿)
   - [3.8 密码修改](#38-密码修改)
   - [3.9 业务办理](#39-业务办理)
4. [文件爬虫 FileCrawler](#4-文件爬虫-filecrawler)
   - [4.1 基本用法](#41-基本用法)
   - [4.2 爬取策略](#42-爬取策略)
   - [4.3 过滤与提前停止](#43-过滤与提前停止)
   - [4.4 并发下载](#44-并发下载)
   - [4.5 下载记录与断点续爬](#45-下载记录与断点续爬)
   - [4.6 输出目录结构](#46-输出目录结构)
5. [类型参考](#5-类型参考)
6. [异常处理](#6-异常处理)
7. [最佳实践](#7-最佳实践)

---

## 1. 安装

> **要求：** Node.js >= 18

```bash
npm install @gxuwjxt/node
# or
pnpm add @gxuwjxt/node
# or
yarn add @gxuwjxt/node
```

开发安装（从源码）：

```bash
git clone https://github.com/halfaradish/GxuWjxtClient.git
cd GxuWjxtClient
pnpm install
pnpm build:node
```

**依赖：** cheerio, iconv-lite

---

## 2. 配置

SDK 提供三种配置方式，优先级为：**构造函数参数 > 环境变量 > 配置文件 > 默认值**。

### 方式 A：构造函数传参（推荐）

```typescript
import { WjxtClient, WjxtConfig } from '@gxuwjxt/node';

// 直接传参
const client = new WjxtClient({
  username: 'your_student_id',
  password: 'your_password',
});

// 使用配置对象
const config = new WjxtConfig({
  username: 'your_student_id',
  password: 'your_password',
  timeout: 60_000,        // 60 秒
  downloadDir: './my_downloads',
});
const client2 = new WjxtClient({ config });
```

### 方式 B：环境变量

```bash
export WJXT_USERNAME=your_student_id
export WJXT_PASSWORD=your_password
export WJXT_BASE_URL=https://wjxt.gxu.edu.cn   # 可选
export WJXT_MYTEIP=172.28.222.133--2            # 可选
export WJXT_DOWNLOAD_DIR=./downloads            # 可选
```

```typescript
import { WjxtConfig } from '@gxuwjxt/node';

const config = WjxtConfig.fromEnv();
const client = new WjxtClient({ config });
```

### 方式 C：配置文件

```typescript
import { WjxtConfig } from '@gxuwjxt/node';

const config = WjxtConfig.fromFile('./config.json');
const client = new WjxtClient({ config });
```

配置文件格式：

```json
{
  "username": "your_student_id",
  "password": "your_password",
  "base_url": "https://wjxt.gxu.edu.cn",
  "myteip": "172.28.222.133--2",
  "download_dir": "./downloads"
}
```

### WjxtConfig 完整字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `username` | `string` | `""` | 学号/用户名 |
| `password` | `string` | `""` | 密码 |
| `baseUrl` | `string` | `"https://wjxt.gxu.edu.cn"` | 系统根地址 |
| `myteip` | `string` | `"172.28.222.133--2"` | 办公 IP 标识 |
| `timeout` | `number` | `30000` | HTTP 请求超时（**毫秒**） |
| `retryCount` | `number` | `3` | 请求失败重试次数 |
| `retryDelay` | `number` | `2000` | 重试间隔（**毫秒**） |
| `downloadDir` | `string` | `"./downloads"` | 默认下载目录 |
| `pageDelay` | `number` | `500` | 翻页间隔（**毫秒**） |
| `historyFile` | `string` | `"download_history.json"` | 下载记录文件名 |
| `maxConcurrency` | `number` | `1` | 并发请求数 |
| `userAgent` | `string` | Chrome 120 UA | HTTP User-Agent |

> **适配说明：** `timeout`、`retryDelay`、`pageDelay` 单位为**毫秒**（Python SDK 为秒），与 Node.js 生态的 `setTimeout`、`AbortSignal.timeout` 保持一致。

`mergeWith()` 方法基于当前配置创建覆盖副本：

```typescript
const prodConfig = config.mergeWith({ timeout: 60_000, retryCount: 5 });
```

---

## 3. 客户端 WjxtClient

> **与 Python SDK 的差异：** Node.js 只有单一 `WjxtClient` 类，所有方法返回 `Promise`。
> 不存在独立的同步/异步客户端，因为 Node.js I/O 模型天然是异步的。

### 3.1 生命周期

推荐使用 `using` 语法 (TypeScript 5.2+) 或手动管理，确保客户端正确关闭：

```typescript
import { WjxtClient } from '@gxuwjxt/node';

// 方式 A: using 语法 (TS 5.2+)
{
  using client = new WjxtClient({ username: '学号', password: '密码' });
  await client.login();
  // ...
} // 自动调用 close()

// 方式 B: try/finally
const client = new WjxtClient({ username: '学号', password: '密码' });
try {
  await client.login();
  // ...
} finally {
  await client.logout();
  client.close();
}
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `client.baseUrl` | `string` | 系统根地址 |
| `client.wjxtUi` | `string` | 主应用路径 (`{baseUrl}/Wjxt_UI`) |
| `client.loggedIn` | `boolean` | 是否已登录 |

### 3.2 认证

```typescript
// 登录 — 返回 Promise<boolean>
const success = await client.login();
if (!success) {
  console.log('登录失败');
}

// 退出
await client.logout();
```

登录成功后会维持 `ASP.NET_SessionId` Cookie，SDK 内部自动管理（Node.js 的 `fetch` 不维护 Cookie jar，SDK 手动解析 `Set-Cookie` 头并缓存）。SDK 默认启用 `autoRelogin`，会话过期时自动重新登录并重试请求（最多一次）。可通过 `WjxtConfig({ autoRelogin: false })` 禁用，此时会抛出 `SessionExpiredError`。

### 3.3 部门列表

```typescript
const depts = await client.getDepartments();
for (const d of depts) {
  console.log(`ID: ${d.id}  名称: ${d.tnDecoded}  类型: ${d.type}`);
}
```

每个部门是一个 `DepartmentInfo` 对象：

```typescript
interface DepartmentInfo {
  id: number;           // 部门 ID（如 16 表示学工部）
  type: number;         // 部门类型
  tnEncoded: string;    // GB2312 URL 编码后的名称
  tnDecoded: string;    // 解码后的可读名称
  url: string;          // 该部门文件列表的完整 URL
}
```

### 3.4 文件列表与遍历

#### 单页获取

```typescript
const [files, pageInfo] = await client.getFileListStructured(1);

console.log(`第 ${pageInfo.currentPage}/${pageInfo.totalPages} 页`);
console.log(`每页 ${pageInfo.perPage} 条，共 ${pageInfo.totalItems} 条`);

for (const f of files) {
  console.log(`[${f.index}] ${f.department}: ${f.title} (${f.date})`);
  console.log(`  ID: ${f.id}, 未读: ${f.isUnread}`);
}
```

#### 惰性遍历（AsyncGenerator，自动翻页）

> **适配说明：** Python 的 `Iterator[FileInfo]` → Node.js 的 `AsyncGenerator<FileInfo>`。
> 使用 `for await...of` 遍历，惰性加载，内存友好。

```typescript
// 遍历全部文件
for await (const f of client.iterFiles({ maxPages: 10 })) {
  console.log(`[${f.index}] ${f.department}: ${f.title}`);
}

// 遍历指定部门的文件
for await (const f of client.iterDeptFiles(16, '学工部', { maxPages: 5 })) {
  console.log(`[${f.index}] ${f.title}`);
}
```

> **注意：** Node.js 的 `iterFiles()` 接受 `{ maxPages }` 选项对象，而 Python 版接受 `max_pages` 关键字参数。

#### 低级 API

```typescript
// 获取全部文件页面的原始 HTML
const html = await client.getFileList();

// 获取带翻页参数的原始 HTML
const html2 = await client.getFileList({ listId: 127, listType: 100, listName: '全部文件', page: 3 });

// 获取部门文件的原始 HTML
const html3 = await client.getDeptFiles(16, 0, '学工部', 2);
```

`FileInfo` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `number \| null` | 文件 ID |
| `index` | `string` | 列表中序号 |
| `title` | `string` | 文件标题 |
| `department` | `string` | 发布部门名称 |
| `date` | `string` | 发布日期（`YYYY-MM-DD`） |
| `isUnread` | `boolean` | 是否未读 |
| `detailUrl` | `string` | 详情页完整 URL |

### 3.5 文件详情与下载

#### 获取详情

```typescript
const detail = await client.getFileDetail(61424);

console.log(`标题: ${detail.title}`);
console.log(`正文长度: ${detail.rawHtml.length} 字符`);
console.log(`附件数: ${detail.downloadUrls.length}`);

for (const att of detail.downloadUrls) {
  console.log(`  - ${att.filename}: ${att.url}`);
}
```

`FileDetail` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fileId` | `number` | 文件 ID |
| `title` | `string` | 文件标题 |
| `detailUrl` | `string` | 详情页 URL |
| `rawHtml` | `string` | 正文 HTML 源码 |
| `downloadUrls` | `Attachment[]` | 附件列表 |

`Attachment` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | `string` | 下载链接 |
| `filename` | `string` | 原始文件名 |

#### 下载文件

```typescript
// 通过文件 ID 下载
const filepath = await client.downloadFile({ fileId: 61424, saveDir: './downloads' });
if (filepath) {
  console.log(`已下载到: ${filepath}`);
}

// 通过 URL 直接下载
const path2 = await client.downloadFile({
  url: '/filezip/uploadfile/2026/05/somefile.xlsx',
  saveDir: './downloads',
});
```

`downloadFile` 返回保存路径 (`string`)，失败返回 `null`。

> **适配说明：** Node.js 版 `downloadFile` 接受 `{ fileId?, url?, saveDir? }` 选项对象，而非独立的位置参数。

### 3.6 搜索

```typescript
// 标题搜索
const result = await client.search({ keyword: '奖学金', searchType: 'title' });
console.log(`搜索到 ${result.totalCount} 条, ${result.totalPages} 页`);
for (const f of result.files.slice(0, 5)) {
  console.log(`  [${f.index}] ${f.department}: ${f.title} (${f.date})`);
}

// 全文搜索
const result2 = await client.search({ keyword: '奖学金', searchType: 'content' });

// 组合筛选
const result3 = await client.search({
  keyword: '通知',
  searchType: 'title',
  fileYear: '2026',
  fileType: '16',          // 学工部
  matchMode: 'Fuzzy',
});

// 翻页
const page2 = await client.search({ keyword: '考试' }, 2);

// 惰性遍历搜索结果（AsyncGenerator，自动翻页）
for await (const f of client.iterSearch({ keyword: '2026' }, { maxPages: 3 })) {
  console.log(f.title);
}
```

**搜索参数 (`SearchParams`):**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | `string` | `""` | 搜索关键词 |
| `searchType` | `string` | `"title"` | `"title"` / `"fileNum"` / `"content"` |
| `fileType` | `string` | `"全部文件"` | 全部/前一周/前一个月/部门 ID |
| `fileYear` | `string` | `"0"` | `"0"` = 全部年份, 或 `"2026"` 等 |
| `matchMode` | `string` | `"Fuzzy"` | `"Fuzzy"` 模糊 / `"Accurate"` 精确 |

**返回 (`SearchResult`):**

| 字段 | 类型 | 说明 |
|------|------|------|
| `files` | `FileInfo[]` | 当前页文件列表 |
| `totalCount` | `number` | 搜索结果总数 |
| `currentPage` | `number` | 当前页码 |
| `totalPages` | `number` | 总页数 |
| `perPage` | `number` | 每页条数（固定 50） |

### 3.7 电话簿

```typescript
const contacts = await client.parsePhoneList();
for (const c of contacts) {
  console.log(`${c.name}: ${c.phone}  ${c.extra}`);
}

// 分步操作
const html = await client.getPhoneList();
const contacts2 = await client.parsePhoneList(html);
```

`PhoneContact` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `string` | 联系人姓名 |
| `phone` | `string` | 电话号码 |
| `extra` | `string` | 附加信息（`\|` 分隔） |

### 3.8 密码修改

```typescript
const success = await client.changePassword('old_password', 'NewPwd@123');
```

> **密码要求：** 必须包含大写字母、小写字母、数字、特殊字符，长度 8-30 位。

### 3.9 业务办理

```typescript
// 各业务页面均返回 BusinessPage 结构
const todoPage = await client.getTodoList();
console.log(`待办: 标签="${todoPage.activeTab}", 记录=${todoPage.records.length}条`);

const donePage = await client.getTodoProcessing();
const myUpdates = await client.getMyUpdateLists();

// 获取新建业务表单（只读查看表单结构）
const addPage = await client.getBusinessAddPage();
console.log(`表单页面 ${addPage.rawHtml.length} 字节`);

// 提交新业务（⚠️ 会创建真实业务工单，谨慎使用）
// const response = await client.addBusiness({
//   field_name: 'value',
// });
```

`BusinessPage` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `pageType` | `string` | 页面标识 |
| `pageTitle` | `string` | 页面标题 |
| `activeTab` | `string` | 当前激活的导航标签 |
| `navLinks` | `Record<string, string>` | 标签名 → URL 映射 |
| `records` | `BusinessRecord[]` | 数据行 |
| `totalCount` | `number` | 总记录数 |
| `hasSearch` | `boolean` | 是否有搜索框 |
| `rawHtml` | `string` | 原始 HTML |

---

## 4. 文件爬虫 FileCrawler

`FileCrawler` 是高层封装，提供批量下载、过滤、并发、下载记录等功能。

> **适配说明：** Python 的 `ThreadPoolExecutor`（多线程）→ Node.js 的信号量模式（Promise 异步并发）。
> 参数 `workers` → `concurrency`，`page_delay`（秒）→ `pageDelay`（毫秒）。

### 4.1 基本用法

```typescript
import { WjxtClient, FileCrawler } from '@gxuwjxt/node';

const client = new WjxtClient({ username: '学号', password: '密码' });
await client.login();

const crawler = new FileCrawler(client, {
  downloadDir: './downloads',
  concurrency: 8,    // 并发下载数
  pageDelay: 500,    // 翻页间隔（毫秒）
});

const stats = await crawler.crawlAll({ unreadOnly: true });
console.log(`下载: ${stats.downloaded}, 跳过: ${stats.skipped}`);
```

### 4.2 爬取策略

三种策略覆盖不同使用场景：

#### crawlAll — 全部文件（不分部门）

```typescript
const stats = await crawler.crawlAll({
  maxPages: 10,                              // 最多翻 10 页
  after: new Date('2026-03-01'),             // 只下载此日期之后的文件
  unreadOnly: true,                          // 只下载未读文件
  dryRun: false,                             // true = 预览模式
  maxEmptyPages: 3,                          // 连续 3 页无匹配则停止
});
```

#### crawlDepartment — 指定部门

```typescript
const deptStats = await crawler.crawlDepartment(16, {
  deptName: '学工部（处）、武装部（就业中心）',
  maxPages: 5,
  unreadOnly: true,
});
```

#### crawlAllDepartments — 遍历所有部门

```typescript
const allStats = await crawler.crawlAllDepartments({
  maxPages: 3,       // 每个部门最多翻 3 页
  unreadOnly: true,
});
```

遍历所有部门时，某个部门出错不会中断整体流程（错误会被打印并跳过）。

### 4.3 过滤与提前停止

#### 过滤参数

- **`unreadOnly: true`**：只下载标记为"未读"的文件
- **`after: new Date(...)`**：只下载该日期（含）之后的文件

```typescript
// 组合过滤
const stats = await crawler.crawlAll({
  after: new Date('2026-03-01'),
  unreadOnly: true,
});
```

#### 提前停止 (`maxEmptyPages`)

翻页过程中，如果连续 N 页没有任何文件满足过滤条件，爬虫会自动停止。默认 3，设 0 禁用。

```typescript
// 连续 3 页无匹配即停（默认）
crawler.crawlAll({ unreadOnly: true });

// 连续 5 页才停
crawler.crawlAll({ unreadOnly: true, maxEmptyPages: 5 });

// 禁用提前停止
crawler.crawlAll({ unreadOnly: true, maxEmptyPages: 0 });
```

### 4.4 并发下载

```typescript
const crawler = new FileCrawler(client, {
  downloadDir: './downloads',
  concurrency: 8,    // 同时 8 个下载请求
});
```

- `concurrency: 1`（默认）：串行下载，显示进度条
- `concurrency > 1`：异步并发下载，信号量控制

进度条示例：

```
  [████████████░░░░░░░░] 8/10  80%
```

> **注意：** 过高的并发数可能导致服务器限流。建议从 3-5 开始尝试。

### 4.5 下载记录与断点续爬

爬虫在下载目录自动维护 `download_history.json`。每个文件通过 `md5("wjxt_file_{file_id}")` 生成唯一哈希，已下载的文件在后续运行中自动跳过。

```typescript
// 清除下载记录
crawler.clearHistory();

// 查看已下载列表
console.log(`已下载 ${crawler.history.size} 个文件`);
```

### 4.6 输出目录结构

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
└── 校团委/
    └── ...
```

---

## 5. 类型参考

### PaginationInfo

```typescript
interface PaginationInfo {
  currentPage: number;     // 当前页码
  totalPages: number;      // 总页数
  perPage: number;         // 每页条目数（固定 50）
  totalItems: number;      // 符合条件的总条目数
}
```

### FileInfo

```typescript
interface FileInfo {
  id: number | null;       // 文件 ID（部分行可能为 null）
  index: string;           // 序号
  title: string;           // 标题
  department: string;      // 发布部门
  date: string;            // 日期（YYYY-MM-DD）
  isUnread: boolean;       // 是否有 [未读] 标记
  detailUrl: string;       // 详情页完整 URL
}
```

### FileDetail

```typescript
interface FileDetail {
  fileId: number;              // 文件 ID
  title: string;               // 标题
  detailUrl: string;           // 详情页 URL
  rawHtml: string;             // 正文 HTML
  downloadUrls: Attachment[];  // 附件列表
}

interface Attachment {
  url: string;      // 下载 URL
  filename: string; // 原始文件名
}
```

### SearchParams

```typescript
interface SearchParams {
  keyword: string;
  searchType: 'title' | 'fileNum' | 'content';
  fileType: string;
  fileYear: string;
  matchMode: 'Accurate' | 'Fuzzy';
}
```

### SearchResult

```typescript
interface SearchResult {
  files: FileInfo[];
  totalCount: number;
  currentPage: number;
  totalPages: number;
  perPage: number;
}
```

### CrawlStats

```typescript
interface CrawlStats {
  totalFiles: number;      // 扫描的文件总数
  downloaded: number;      // 本次新下载的文件数
  skipped: number;         // 已在历史记录中跳过的文件数
  noAttachment: number;    // 无附件的文件数
  failed: number;          // 下载失败的文件数
}
```

---

## 6. 异常处理

```typescript
import {
  WjxtError, AuthError, NetworkError, ParseError,
  SessionExpiredError, DownloadError,
} from '@gxuwjxt/node';

try {
  await client.login();
  const [files] = await client.getFileListStructured(1);
} catch (e) {
  if (e instanceof AuthError) {
    console.error('认证失败：用户名或密码错误');
  } else if (e instanceof SessionExpiredError) {
    console.error('会话过期：需要重新登录');
  } else if (e instanceof NetworkError) {
    console.error('网络错误：无法连接到服务器');
  } else if (e instanceof ParseError) {
    console.error('解析错误：页面结构可能发生了变化');
  } else if (e instanceof DownloadError) {
    console.error('下载失败：文件不存在或权限不足');
  } else if (e instanceof WjxtError) {
    console.error(`SDK 错误: ${e.message}`);
  }
}
```

异常层次结构：

```
Error
└── WjxtError
    ├── AuthError           # 登录失败
    ├── NetworkError        # 网络请求失败
    ├── ParseError          # HTML 解析失败
    ├── SessionExpiredError # 会话过期
    └── DownloadError       # 文件下载失败
```

> 会话过期自动重连默认已启用 (`autoRelogin: true`)，通常无需手动处理 `SessionExpiredError`。

---

## 7. 最佳实践

### 管理客户端生命周期

```typescript
// 推荐：using 语法 (TS 5.2+)
{
  using client = new WjxtClient({ username: '学号', password: '密码' });
  await client.login();
  // ...
}

// 或 try/finally
const client = new WjxtClient({ username: '学号', password: '密码' });
try {
  await client.login();
  // ...
} finally {
  client.close();
}
```

### 注意翻页间隔

系统每页 50 条记录，翻页过于频繁可能被服务器限制。默认 `pageDelay=500`（毫秒），如需加速请适度调整。

### 善用过滤减少请求

```typescript
// 差：翻完 295 页找 3 个未读文件
await crawler.crawlAll({ unreadOnly: true, maxEmptyPages: 0 });

// 好：发现连续 3 页无未读就停
await crawler.crawlAll({ unreadOnly: true, maxEmptyPages: 3 });

// 更好：加日期过滤缩小范围
await crawler.crawlAll({
  after: new Date('2026-05-01'),
  unreadOnly: true,
  maxEmptyPages: 3,
});
```

### 断点续爬

```typescript
// 每周运行一次，只下载本周新发布的未读文件
const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
const stats = await crawler.crawlAll({ after: lastWeek, unreadOnly: true });
```

### 先预览再下载

```typescript
// 第一步：预览
await crawler.crawlAll({ unreadOnly: true, dryRun: true });

// 确认无误后再实际下载
await crawler.crawlAll({ unreadOnly: true, dryRun: false });
```

### 处理中断

爬虫支持 `Ctrl+C` 安全中断。已完成下载的文件会被记录到 `download_history.json`，下次运行自动跳过：

```typescript
try {
  const stats = await crawler.crawlAll({ unreadOnly: true });
} catch (e) {
  if (e instanceof Error && e.name === 'AbortError') {
    console.log('\n已中断。下载记录已保存，下次运行将从断点继续。');
  }
}
```
