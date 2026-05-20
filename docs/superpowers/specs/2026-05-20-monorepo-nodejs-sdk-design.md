# Monorepo 重构 & Node.js SDK 设计文档

**日期**: 2026-05-20
**状态**: 已批准
**分支**: main → 重构

---

## 1. 目标

将单包 Python SDK 项目重构为多语言 Monorepo，并新建功能完全对等的 Node.js (TypeScript) SDK。

### 非目标

- 不修改 Python 业务逻辑
- 不重构 CLI（可后续迭代）
- Node.js SDK 第一版不包含 CLI（后续迭代）

---

## 2. 技术选型

| 决策 | 选择 | 原因 |
|------|------|------|
| Monorepo 工具 | pnpm workspaces | 社区标准，磁盘高效，原生 workspace 协议 |
| Node.js 语言 | TypeScript 5.x | 类型安全，TSDoc 注释，编译输出 .d.ts |
| 构建工具 | tsup (esbuild) | 快速 TypeScript 构建，支持 ESM/CJS 双输出 |
| HTML 解析 | cheerio | API 等价 bs4 + BeautifulSoup |
| 编码处理 | iconv-lite | GB2312 编解码 |
| HTTP 客户端 | `fetch` (Node 18+ built-in) | 零依赖，原生异步 |
| 测试框架 | vitest | 快速、TypeScript 原生、Vite 生态 |
| 包命名 (npm) | `@gxuwjxt/node` | 带 scope，与 Python `gxu-wjxt` 对应 |

---

## 3. 目录结构

```
wjxt/                              # Monorepo 根
├── pnpm-workspace.yaml
├── package.json                   # root scripts
├── .gitignore
├── README.md                      # 多语言入口
├── LICENSE
├── docs/
│   ├── GUIDE.md
│   ├── api.md
│   └── superpowers/specs/
├── packages/
│   ├── python/                    # gxu-wjxt (迁移自根目录)
│   │   ├── pyproject.toml
│   │   ├── Makefile
│   │   ├── demo.py
│   │   ├── config.example.json
│   │   └── src/gxu_wjxt/          # 9 个 .py 文件，业务逻辑不变
│   │       ├── __init__.py
│   │       ├── client.py
│   │       ├── async_client.py
│   │       ├── _base.py
│   │       ├── config.py
│   │       ├── types.py
│   │       ├── exceptions.py
│   │       ├── crawler.py
│   │       └── cli.py
│   └── node/                      # @gxuwjxt/node (新建)
│       ├── package.json
│       ├── tsconfig.json
│       ├── src/
│       │   ├── index.ts           # 公开 API
│       │   ├── client.ts          # HTTP 客户端 (async only)
│       │   ├── types.ts           # 数据模型
│       │   ├── config.ts          # 配置管理
│       │   ├── exceptions.ts      # 异常体系
│       │   ├── crawler.ts         # 文件下载爬虫
│       │   └── _base.ts           # HTML 解析/编码
│       └── test/
│           └── client.test.ts
```

---

## 4. Python → Node.js 映射总表

### 4.1 模块对应

| Python 模块 | Node.js 模块 | 差异说明 |
|------------|-------------|---------|
| `client.py` (WjxtClient) | `client.ts` (WjxtClient) | 合并 sync+async 为单一类，全部 async |
| `async_client.py` | (合并入 client.ts) | Node.js 天然异步，无需独立版本 |
| `_base.py` | `_base.ts` | HTML 解析 (cheerio)、GB2312 编码 (iconv-lite) |
| `config.py` | `config.ts` | timeout/pageDelay 单位秒→毫秒 |
| `types.py` | `types.ts` | `@dataclass` → TypeScript `interface` |
| `exceptions.py` | `exceptions.ts` | ES6 Error 子类化 |
| `crawler.py` | `crawler.ts` | ThreadPoolExecutor → Promise 并发 + 信号量 |
| `cli.py` | 第一版不实现 | 后续迭代 |

### 4.2 库等价

| Python 依赖 | Node.js 等价 | 版本 |
|------------|-------------|------|
| `httpx>=0.27.0` | `fetch` (built-in Node 18+) | — |
| `beautifulsoup4>=4.12.0` | `cheerio` | ^1.0 |
| (标准库 `urllib.parse`) | `iconv-lite` | ^0.6 |
| (标准库 `hashlib`) | `node:crypto` | — |
| (标准库 `json`) | `JSON` / `node:fs` | — |
| (标准库 `pathlib`) | `node:path`, `node:fs/promises` | — |

---

## 5. Node.js API 设计

### 5.1 WjxtClient

```typescript
class WjxtClient {
  constructor(opts?: {
    username?: string;
    password?: string;
    config?: WjxtConfig;
  });

  // === 认证 ===
  async login(): Promise<boolean>;
  async logout(): Promise<boolean>;
  get loggedIn(): boolean;

  // === 导航 ===
  async getMainPage(): Promise<string>;
  async getSidebar(): Promise<string>;
  async getDepartments(): Promise<DepartmentInfo[]>;

  // === 文件列表 ===
  async getFileList(page?: number, listId?: number, listType?: number,
                    listName?: string): Promise<string>;
  getFileListStructured(page?: number): Promise<[FileInfo[], PaginationInfo]>;
  iterFiles(maxPages?: number): AsyncGenerator<FileInfo>;

  // === 部门文件 ===
  async getDeptFiles(deptId: number, deptType?: number,
                     deptName?: string, page?: number): Promise<string>;
  iterDeptFiles(deptId: number, deptName?: string,
                maxPages?: number): AsyncGenerator<FileInfo>;

  // === 文件详情 & 下载 ===
  async getFileDetail(fileId: number): Promise<FileDetail>;
  async downloadFile(opts: {
    fileId?: number; url?: string; saveDir?: string;
  }): Promise<string | null>;

  // === 搜索 ===
  async search(params?: SearchParams, page?: number): Promise<SearchResult>;
  iterSearch(params?: SearchParams, maxPages?: number): AsyncGenerator<FileInfo>;

  // === 用户管理 ===
  async changePassword(oldPwd: string, newPwd: string): Promise<boolean>;

  // === 电话簿 ===
  async parsePhoneList(html?: string): Promise<PhoneContact[]>;

  // === 业务办理 ===
  async getTodoList(): Promise<BusinessPage>;
  async getTodoProcessing(): Promise<BusinessPage>;
  async getMyTodoLists(): Promise<BusinessPage>;
  async getMyUpdateLists(): Promise<BusinessPage>;
  async getBusinessAddPage(): Promise<BusinessPage>;
  async addBusiness(formData: Record<string, string>): Promise<string>;

  // === 生命周期 ===
  close(): void;
  [Symbol.dispose](): void;        // TS 5.2+ "using" 语法
  get baseUrl(): string;
}
```

### 5.2 FileCrawler

```typescript
class FileCrawler {
  constructor(client: WjxtClient, opts?: {
    downloadDir?: string;
    concurrency?: number;          // 对应 Python workers
    pageDelay?: number;            // ms
  });

  static filterFiles(files: FileInfo[], opts?: {
    after?: Date; unreadOnly?: boolean;
  }): FileInfo[];

  async downloadOne(fileInfo: FileInfo, dryRun?: boolean): Promise<string | null>;
  async downloadBatch(files: FileInfo[], dryRun?: boolean): Promise<CrawlStats>;

  async crawlAll(opts?: CrawlOptions): Promise<CrawlStats>;
  async crawlDepartment(deptId: number, opts?: CrawlOptions): Promise<CrawlStats>;
  async crawlAllDepartments(opts?: CrawlOptions): Promise<CrawlStats>;

  clearHistory(): void;
}
```

### 5.3 类型定义

```typescript
interface PaginationInfo {
  currentPage: number;     // default 1
  totalPages: number;      // default 1
  perPage: number;         // default 50
  totalItems: number;      // default 0
}

interface FileInfo {
  id: number | null;
  index: string;
  title: string;
  department: string;
  date: string;            // "YYYY-MM-DD"
  isUnread: boolean;
  detailUrl: string;
}

interface Attachment {
  url: string;
  filename: string;
}

interface FileDetail {
  fileId: number;
  title: string;
  detailUrl: string;
  rawHtml: string;
  downloadUrls: Attachment[];
}

interface SearchParams {
  keyword: string;
  searchType: "title" | "fileNum" | "content";
  fileType: string;
  fileYear: string;
  matchMode: "Accurate" | "Fuzzy";
}

interface SearchResult {
  files: FileInfo[];
  totalCount: number;
  currentPage: number;
  totalPages: number;
  perPage: number;
}

interface DepartmentInfo {
  id: number;
  type: number;
  tnEncoded: string;
  tnDecoded: string;
  url: string;
}

interface PhoneContact {
  name: string;
  phone: string;
  extra: string;
}

interface BusinessRecord {
  rowIndex: number;
  cells: string[];
}

interface BusinessPage {
  pageType: string;
  activeTab: string;
  navLinks: Record<string, string>;
  records: BusinessRecord[];
  totalCount: number;
  hasSearch: boolean;
  rawHtml: string;
}

interface CrawlStats {
  totalFiles: number;
  downloaded: number;
  skipped: number;
  noAttachment: number;
  failed: number;
  // incDownloaded(), incSkipped(), incNoAttachment(), incFailed()
}

interface CrawlOptions {
  maxPages?: number;
  after?: Date;
  unreadOnly?: boolean;
  dryRun?: boolean;
  maxEmptyPages?: number;    // default 3
}
```

### 5.4 异常体系

```typescript
class WjxtError extends Error {
  constructor(message: string, cause?: Error);
}

class AuthError extends WjxtError {}
class NetworkError extends WjxtError {}
class ParseError extends WjxtError {}
class SessionExpiredError extends WjxtError {}
class DownloadError extends WjxtError {}
```

### 5.5 配置

```typescript
class WjxtConfig {
  username: string;                    // default ""
  password: string;                    // default ""
  baseUrl: string;                     // "https://wjxt.gxu.edu.cn"
  myteip: string;                      // "172.28.222.133--2"
  timeout: number;                     // 30000 (ms)
  maxRedirects: number;               // 5
  verifySsl: boolean;                  // false
  retryCount: number;                  // 3
  retryDelay: number;                  // 2000 (ms)
  autoRelogin: boolean;                // true
  downloadDir: string;                 // "./downloads"
  pageDelay: number;                   // 500 (ms)
  historyFile: string;                 // "download_history.json"
  maxConcurrency: number;             // 1
  userAgent: string;

  static fromEnv(): WjxtConfig;
  static fromFile(path: string): WjxtConfig;
  mergeWith(overrides: Partial<WjxtConfig>): WjxtConfig;
}
```

---

## 6. 关键适配点

### 6.1 Cookie 管理

Python `httpx.Client` 自动维护 cookie jar。Node.js `fetch` 不管理 cookie。

**方案**：客户端内部维护 `Map<string, string>` cookie 存储，每次响应解析 `Set-Cookie` 头，每次请求设置 `Cookie` 头。

### 6.2 编码处理

ASP.NET 后端使用 GB2312。Node.js 没有原生 GB2312 支持。

**方案**：
- 响应解码：`iconv-lite.decode(Buffer, 'gb2312')`
- POST 编码：`iconv-lite.encode(value, 'gb2312')` + URL 编码

### 6.3 并发控制

Python 使用 `ThreadPoolExecutor` 进行多线程下载。Node.js 是单线程异步模型。

**方案**：用信号量模式（计数器 + Promise 队列）限制同时进行的 fetch 请求数，等价于 Python 的 `workers` 参数。

### 6.4 迭代器

Python `Iterator[FileInfo]` → Node.js `AsyncGenerator<FileInfo>`

用户用法：
```typescript
for await (const file of client.iterFiles()) {
  console.log(file.title);
}
```

### 6.5 会话自动重连

Python 中的 `_check_session` 递归调用模式，在 Node.js 中用 **闭包重试** 实现：

```typescript
private async _checkSession<T>(
  html: string,
  retryFn: () => Promise<string>
): Promise<string> {
  if (!isSessionExpired(html)) return html;
  if (!this._config.autoRelogin) throw new SessionExpiredError(...);
  await this.login();
  const html2 = await retryFn();
  if (isSessionExpired(html2)) throw new SessionExpiredError(...);
  return html2;
}
```

---

## 7. pnpm workspace 配置

### pnpm-workspace.yaml

```yaml
packages:
  - 'packages/*'
```

### 根 package.json

```json
{
  "name": "gxu-wjxt-monorepo",
  "private": true,
  "scripts": {
    "build:node": "pnpm -F @gxuwjxt/node build",
    "test:node": "pnpm -F @gxuwjxt/node test",
    "build:python": "cd packages/python && pip install -e .",
    "dev:node": "pnpm -F @gxuwjxt/node dev"
  }
}
```

### packages/node/package.json（关键字段）

```json
{
  "name": "@gxuwjxt/node",
  "version": "1.2.0",
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts"
    }
  },
  "engines": { "node": ">=18" },
  "dependencies": {
    "cheerio": "^1.0.0",
    "iconv-lite": "^0.6.3"
  },
  "devDependencies": {
    "tsup": "^8.0.0",
    "typescript": "^5.4.0",
    "vitest": "^1.0.0",
    "@types/node": "^20.0.0"
  }
}
```

---

## 8. 实施清单

1. 创建 `packages/python/` 目录，迁移根目录 Python 代码
2. 更新 `.gitignore`
3. 创建 `pnpm-workspace.yaml` 和根 `package.json`
4. 更新 `README.md` 为多语言入口
5. 创建 `packages/node/` 骨架 (`package.json`, `tsconfig.json`)
6. 实现 `src/types.ts` — 数据模型
7. 实现 `src/exceptions.ts` — 异常体系
8. 实现 `src/config.ts` — 配置管理
9. 实现 `src/_base.ts` — HTML 解析、GB2312 编码工具
10. 实现 `src/client.ts` — HTTP 客户端（全部 19 个 API）
11. 实现 `src/crawler.ts` — 文件下载爬虫
12. 实现 `src/index.ts` — 公开 API 导出
13. 实现 `test/client.test.ts` — 基础单元测试
14. 验证：`pnpm install && pnpm build:node && pnpm test:node`
15. 验证：Python 包 `pip install -e packages/python/` 可正常运行
