# Monorepo 重构 & Node.js SDK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure repo as pnpm monorepo, migrate Python SDK to packages/python/, build Node.js TypeScript SDK with feature parity in packages/node/

**Architecture:** Two packages under `packages/` directory — Python (`gxu-wjxt`) and Node.js (`@gxuwjxt/node`). Python code is moved unchanged from root. Node.js SDK uses `fetch` + `cheerio` + `iconv-lite` stack, single async client (no separate sync/async), `AsyncGenerator` for lazy pagination, semaphore-based concurrency control for crawler.

**Tech Stack:** pnpm workspaces, TypeScript 5.x, tsup, cheerio, iconv-lite, vitest, Node 18+

---

### Task 1: Create monorepo root config files

**Files:**
- Create: `pnpm-workspace.yaml`
- Create: `package.json` (root — update existing if present; there is none)
- Modify: `.gitignore`

- [ ] **Step 1: Write pnpm-workspace.yaml**

```yaml
packages:
  - 'packages/*'
```

- [ ] **Step 2: Write root package.json**

```json
{
  "name": "gxu-wjxt-monorepo",
  "private": true,
  "scripts": {
    "build:node": "pnpm -r --filter @gxuwjxt/node build",
    "test:node": "pnpm -r --filter @gxuwjxt/node test",
    "dev:node": "pnpm -r --filter @gxuwjxt/node dev"
  }
}
```

- [ ] **Step 3: Update .gitignore — append Node.js patterns**

Current `.gitignore`:
```
config.json
downloads/
__pycache__/
*.pyc
download_history.json
*.egg-info/
/dist
__test__/
```

Append:
```
# Node.js
node_modules/
packages/node/dist/
packages/node/*.tsbuildinfo
```

- [ ] **Step 4: Commit**

```bash
git add pnpm-workspace.yaml package.json .gitignore
git commit -m "chore: add monorepo root config (pnpm workspaces)"
```

---

### Task 2: Migrate Python SDK to packages/python/

**Files:**
- Create: `packages/python/pyproject.toml` (updated paths)
- Move: `src/` → `packages/python/src/`
- Move: `demo.py` → `packages/python/demo.py`
- Move: `Makefile` → `packages/python/Makefile`
- Move: `config.example.json` → `packages/python/config.example.json`

- [ ] **Step 1: Create packages/python/ directory structure**

```bash
mkdir -p packages/python
```

- [ ] **Step 2: Move Python source files**

```bash
mv src packages/python/
mv demo.py packages/python/
mv Makefile packages/python/
mv config.example.json packages/python/
```

- [ ] **Step 3: Update pyproject.toml — change package-dir from ""="src" to ""="src" (unchanged, already relative)**

The existing `pyproject.toml` already has `package-dir = {"" = "src"}` which is relative to the file location. After moving, it works as-is. Verify:

```ini
[tool.setuptools]
package-dir = {"" = "src"}
packages = ["gxu_wjxt"]
```

No change needed — the config is relative to `pyproject.toml` location.

- [ ] **Step 4: Remove leftover __pycache__ and __test__ from root**

```bash
rm -rf __pycache__ __test__
```

- [ ] **Step 5: Commit**

```bash
git add packages/python/ .gitignore
git rm -r src/ demo.py Makefile config.example.json __pycache__/ __test__/ 2>/dev/null; true
git commit -m "refactor: move Python SDK to packages/python/"
```

---

### Task 3: Update top-level files after migration

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml` → moved to `packages/python/` (already done in Task 2)

- [ ] **Step 1: Update README.md — replace 项目结构 section**

Replace the tree block in README.md (lines 28-52) with:

```markdown
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
│   └── node/                   # @gxuwjxt/node TypeScript SDK
│       ├── package.json
│       ├── tsconfig.json
│       └── src/                # 核心包（7个模块）
```

And add after the Python install section:

```markdown
## Node.js SDK

```bash
npm install @gxuwjxt/node
# or
pnpm add @gxuwjxt/node
```

```typescript
import { WjxtClient } from '@gxuwjxt/node';

const client = new WjxtClient({ username: 'student_id', password: 'password' });
await client.login();

for await (const file of client.iterFiles({ maxPages: 3 })) {
  console.log(file.title);
}
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for monorepo structure and Node.js SDK"
```

---

### Task 4: Verify Python package integrity

**Files:**
- Verify: `packages/python/src/gxu_wjxt/` exists with all 9 files

- [ ] **Step 1: Check all Python source files present**

```bash
ls packages/python/src/gxu_wjxt/
```

Expected: `__init__.py  _base.py  async_client.py  cli.py  client.py  config.py  crawler.py  exceptions.py  types.py`

- [ ] **Step 2: Check Python syntax is valid**

```bash
python -c "import sys; sys.path.insert(0, 'packages/python/src'); from gxu_wjxt import WjxtClient, AsyncWjxtClient, FileCrawler, WjxtConfig; print('All imports OK')"
```

Expected: `All imports OK` (no errors)

- [ ] **Step 3: Commit any fixups if needed, or confirm clean**

```bash
git status
```

---

### Task 5: Create Node.js package skeleton

**Files:**
- Create: `packages/node/package.json`
- Create: `packages/node/tsconfig.json`

- [ ] **Step 1: Write packages/node/package.json**

```json
{
  "name": "@gxuwjxt/node",
  "version": "1.2.0",
  "description": "广西大学文件管理系统 Node.js/TypeScript SDK",
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
  "files": [
    "dist"
  ],
  "scripts": {
    "build": "tsup src/index.ts --format cjs,esm --dts --clean",
    "dev": "tsup src/index.ts --format cjs,esm --dts --watch",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "engines": {
    "node": ">=18"
  },
  "license": "MIT",
  "dependencies": {
    "cheerio": "^1.0.0",
    "iconv-lite": "^0.6.3"
  },
  "devDependencies": {
    "tsup": "^8.0.2",
    "typescript": "^5.4.0",
    "vitest": "^1.6.0",
    "@types/node": "^20.12.0"
  }
}
```

- [ ] **Step 2: Write packages/node/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "lib": ["ES2022"],
    "types": ["node"]
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules", "dist", "test"]
}
```

- [ ] **Step 3: Create src directory**

```bash
mkdir -p packages/node/src packages/node/test
```

- [ ] **Step 4: Install dependencies**

```bash
pnpm install
```

- [ ] **Step 5: Commit**

```bash
git add packages/node/package.json packages/node/tsconfig.json pnpm-lock.yaml
git commit -m "feat(node): add package skeleton with pnpm workspace"
```

---

### Task 6: Implement types.ts

**Files:**
- Create: `packages/node/src/types.ts`

- [ ] **Step 1: Write packages/node/src/types.ts**

```typescript
/**
 * 分页信息
 * Python 对应: PaginationInfo @dataclass
 */
export interface PaginationInfo {
  currentPage: number;
  totalPages: number;
  perPage: number;
  totalItems: number;
}

/**
 * 文件列表项
 * Python 对应: FileInfo @dataclass
 */
export interface FileInfo {
  id: number | null;
  index: string;
  title: string;
  department: string;
  /** 日期字符串，格式 YYYY-MM-DD */
  date: string;
  isUnread: boolean;
  detailUrl: string;
}

/**
 * 附件信息
 * Python 对应: Attachment @dataclass
 */
export interface Attachment {
  url: string;
  filename: string;
}

/**
 * 文件详情
 * Python 对应: FileDetail @dataclass
 *
 * 调用方可通过 downloadUrls[0]?.url 获取首个附件地址，
 * 对应 Python 的 detail.download_url 属性。
 */
export interface FileDetail {
  fileId: number;
  title: string;
  detailUrl: string;
  rawHtml: string;
  downloadUrls: Attachment[];
}

/**
 * 部门信息
 * Python 对应: DepartmentInfo @dataclass
 */
export interface DepartmentInfo {
  id: number;
  type: number;
  tnEncoded: string;
  tnDecoded: string;
  url: string;
}

/**
 * 搜索参数
 * Python 对应: SearchParams @dataclass
 */
export interface SearchParams {
  keyword: string;
  /** "title" | "fileNum" | "content" */
  searchType: string;
  fileType: string;
  /** "0" = 全部年份，或如 "2026" */
  fileYear: string;
  /** "Accurate" | "Fuzzy" */
  matchMode: string;
}

/**
 * 单页搜索结果
 * Python 对应: SearchResult @dataclass
 */
export interface SearchResult {
  files: FileInfo[];
  totalCount: number;
  currentPage: number;
  totalPages: number;
  perPage: number;
}

/**
 * 电话簿联系人
 * Python 对应: PhoneContact @dataclass
 */
export interface PhoneContact {
  name: string;
  phone: string;
  extra: string;
}

/**
 * 单条业务记录（GridView 行）
 * Python 对应: BusinessRecord @dataclass
 */
export interface BusinessRecord {
  rowIndex: number;
  cells: string[];
}

/**
 * 业务办理页面结构化数据
 * Python 对应: BusinessPage @dataclass
 */
export interface BusinessPage {
  pageType: string;
  activeTab: string;
  navLinks: Record<string, string>;
  records: BusinessRecord[];
  totalCount: number;
  hasSearch: boolean;
  rawHtml: string;
}

/**
 * 爬虫统计
 * Python 对应: CrawlStats @dataclass
 */
export interface CrawlStats {
  totalFiles: number;
  downloaded: number;
  skipped: number;
  noAttachment: number;
  failed: number;
}

/** CrawlStats 工厂：创建可变的统计对象 */
export function createCrawlStats(): CrawlStats {
  return {
    totalFiles: 0,
    downloaded: 0,
    skipped: 0,
    noAttachment: 0,
    failed: 0,
  };
}

/**
 * 爬取选项
 * Python 对应: crawl_* 方法的各个关键字参数
 */
export interface CrawlOptions {
  /** 最多翻页数 */
  maxPages?: number;
  /** 日期过滤（仅下载此日期之后的文件） */
  after?: Date;
  /** 仅下载未读文件 */
  unreadOnly?: boolean;
  /** 预览模式（不实际下载） */
  dryRun?: boolean;
  /** 连续 N 页无匹配时自动停止，默认 3，设为 0 禁用 */
  maxEmptyPages?: number;
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/types.ts
git commit -m "feat(node): add data model type definitions"
```

---

### Task 7: Implement exceptions.ts

**Files:**
- Create: `packages/node/src/exceptions.ts`

- [ ] **Step 1: Write packages/node/src/exceptions.ts**

```typescript
/**
 * SDK 异常体系 — 与 Python exceptions.py 一一对应
 *
 * 使用 ES6 Error 子类化模式。Node.js 继承 Error 需设置
 * prototype 链并捕获堆栈，这里用 ES2022+ 的 `new Error(message, { cause })`。
 *
 * Python 对应: WjxtError(Exception)
 */
export class WjxtError extends Error {
  constructor(message: string, cause?: Error) {
    super(message, { cause });
    this.name = 'WjxtError';
  }
}

/** Python 对应: AuthError(WjxtError) */
export class AuthError extends WjxtError {
  constructor(message: string, cause?: Error) {
    super(message, cause);
    this.name = 'AuthError';
  }
}

/** Python 对应: NetworkError(WjxtError) */
export class NetworkError extends WjxtError {
  constructor(message: string, cause?: Error) {
    super(message, cause);
    this.name = 'NetworkError';
  }
}

/** Python 对应: ParseError(WjxtError) */
export class ParseError extends WjxtError {
  constructor(message: string, cause?: Error) {
    super(message, cause);
    this.name = 'ParseError';
  }
}

/** Python 对应: SessionExpiredError(WjxtError) */
export class SessionExpiredError extends WjxtError {
  constructor(message: string, cause?: Error) {
    super(message, cause);
    this.name = 'SessionExpiredError';
  }
}

/** Python 对应: DownloadError(WjxtError) */
export class DownloadError extends WjxtError {
  constructor(message: string, cause?: Error) {
    super(message, cause);
    this.name = 'DownloadError';
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/exceptions.ts
git commit -m "feat(node): add exception class hierarchy"
```

---

### Task 8: Implement config.ts

**Files:**
- Create: `packages/node/src/config.ts`

- [ ] **Step 1: Write packages/node/src/config.ts**

```typescript
import { readFileSync } from 'node:fs';

/**
 * SDK 全局配置
 *
 * 优先级: 构造参数 > 环境变量 > 配置文件 > 默认值
 * Python 对应: WjxtConfig @dataclass
 *
 * 适配说明:
 * - timeout / retryDelay / pageDelay 单位从 Python 的秒改为毫秒，
 *   因为 Node.js 的 setTimeout、AbortSignal.timeout 等 API 均使用毫秒。
 */
export class WjxtConfig {
  username: string;
  password: string;
  baseUrl: string;
  myteip: string;
  timeout: number;
  maxRedirects: number;
  verifySsl: boolean;
  retryCount: number;
  retryDelay: number;
  autoRelogin: boolean;
  downloadDir: string;
  pageDelay: number;
  historyFile: string;
  maxConcurrency: number;
  userAgent: string;

  constructor(overrides: Partial<WjxtConfig> = {}) {
    this.username = overrides.username ?? '';
    this.password = overrides.password ?? '';
    this.baseUrl = overrides.baseUrl ?? 'https://wjxt.gxu.edu.cn';
    this.myteip = overrides.myteip ?? '172.28.222.133--2';
    this.timeout = overrides.timeout ?? 30_000;
    this.maxRedirects = overrides.maxRedirects ?? 5;
    this.verifySsl = overrides.verifySsl ?? false;
    this.retryCount = overrides.retryCount ?? 3;
    this.retryDelay = overrides.retryDelay ?? 2_000;
    this.autoRelogin = overrides.autoRelogin ?? true;
    this.downloadDir = overrides.downloadDir ?? './downloads';
    this.pageDelay = overrides.pageDelay ?? 500;
    this.historyFile = overrides.historyFile ?? 'download_history.json';
    this.maxConcurrency = overrides.maxConcurrency ?? 1;
    this.userAgent = overrides.userAgent ??
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
  }

  /**
   * 从环境变量加载配置
   * Python 对应: WjxtConfig.from_env()
   */
  static fromEnv(): WjxtConfig {
    return new WjxtConfig({
      username: process.env.WJXT_USERNAME ?? '',
      password: process.env.WJXT_PASSWORD ?? '',
      baseUrl: process.env.WJXT_BASE_URL ?? undefined,
      myteip: process.env.WJXT_MYTEIP ?? undefined,
      downloadDir: process.env.WJXT_DOWNLOAD_DIR ?? undefined,
    });
  }

  /**
   * 从 JSON 配置文件加载
   * Python 对应: WjxtConfig.from_file(path)
   */
  static fromFile(path: string): WjxtConfig {
    const data = JSON.parse(readFileSync(path, 'utf-8'));
    return new WjxtConfig({
      username: data.username ?? '',
      password: data.password ?? '',
      baseUrl: data.base_url ?? undefined,
      myteip: data.myteip ?? undefined,
      downloadDir: data.download_dir ?? undefined,
    });
  }

  /**
   * 用给定值覆盖配置字段，返回新实例
   * Python 对应: merge_with(**kwargs)
   */
  mergeWith(overrides: Partial<WjxtConfig>): WjxtConfig {
    return new WjxtConfig({ ...this, ...overrides });
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/config.ts
git commit -m "feat(node): add configuration management"
```

---

### Task 9: Implement _base.ts (Part 1 — encoding + HTML helpers)

**Files:**
- Create: `packages/node/src/_base.ts`

- [ ] **Step 1: Write the first half of _base.ts — encoding and form parsing utilities**

```typescript
/**
 * 内部共享工具 — HTML 解析、GB2312 编码、ASP.NET 表单处理
 * Python 对应: _base.py
 *
 * 适配说明:
 * - BeautifulSoup(html, "html.parser") → cheerio.load(html)，API 高度一致
 * - urllib.parse.quote(name, encoding="gb2312") → iconv-lite 编码后手动 URL 编码
 * - hashlib.md5 → node:crypto createHash
 */

import * as crypto from 'node:crypto';
import * as cheerio from 'cheerio';
import * as iconv from 'iconv-lite';
import type { FileInfo, PaginationInfo, DepartmentInfo, PhoneContact, BusinessPage, BusinessRecord, Attachment } from './types';

// ---------------------------------------------------------------------------
// GB2312 编码
// ---------------------------------------------------------------------------

/** 将字符串编码为 GB2312 URL 编码形式 */
export function encodeGb2312(name: string): string {
  if (!name) return '';
  const buf = iconv.encode(name, 'gb2312');
  let result = '';
  for (const byte of buf) {
    result += '%' + byte.toString(16).toUpperCase().padStart(2, '0');
  }
  return result;
}

/** 解码 GB2312 URL 编码 */
export function decodeGb2312(encoded: string): string {
  if (!encoded) return '';
  // 百分比解码 → Buffer → GB2312 字符串
  const hexStr = encoded.replace(/%/g, '');
  const buf = Buffer.from(hexStr, 'hex');
  return iconv.decode(buf, 'gb2312');
}

/**
 * 将表单字段编码为 GB2312 URL-encoded POST body
 *
 * ASP.NET 服务器端使用 GB2312 解析表单数据，若用 UTF-8 提交中文关键字会导致搜索无结果。
 * 此函数对所有字段名和字段值做 GB2312 编码。
 */
export function encodePostDataGb2312(fields: Record<string, string>): string {
  return Object.entries(fields)
    .map(([k, v]) => `${encodeGb2312(k)}=${encodeGb2312(v)}`)
    .join('&');
}

// ---------------------------------------------------------------------------
// ASP.NET 表单字段提取
// ---------------------------------------------------------------------------

/** 提取 ASP.NET 隐藏表单字段 (VIEWSTATE 等) */
export function extractViewstate(html: string): Record<string, string> {
  const fields: Record<string, string> = {};
  const names = ['__VIEWSTATE', '__VIEWSTATEGENERATOR',
    '__SCROLLPOSITIONX', '__SCROLLPOSITIONY',
    '__EVENTTARGET', '__EVENTARGUMENT'];
  for (const name of names) {
    const re = new RegExp(`name="${name}".*?value="([^"]*)"`);
    const m = html.match(re);
    if (m) fields[name] = m[1]!;
  }
  return fields;
}

/** 提取所有隐藏表单字段 */
export function extractHiddenFields(html: string): Record<string, string> {
  const fields: Record<string, string> = {};
  const re = /<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    fields[m[1]!] = m[2]!;
  }
  return fields;
}

// ---------------------------------------------------------------------------
// 会话过期检测
// ---------------------------------------------------------------------------

/** 检测 HTML 是否表明 ASP.NET 会话已过期 */
export function isSessionExpired(html: string): boolean {
  if (html.length >= 500) return false;
  if (!html.includes('请重新登录') && !html.includes('\\u8bf7\\u91cd\\u65b0\\u767b\\u5f55')) return false;
  return (
    html.includes('default.aspx') &&
    (html.includes('window.location') || html.includes('window.parent'))
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/_base.ts
git commit -m "feat(node): add encoding and form parsing utilities"
```

---

### Task 10: Implement _base.ts (Part 2 — HTML parsing functions)

**Files:**
- Modify: `packages/node/src/_base.ts` (append parsing functions)

- [ ] **Step 1: Append to _base.ts — parseFileList, parsePaginationInfo, parseDepartments**

```typescript
// ---------------------------------------------------------------------------
// 文件列表解析
// ---------------------------------------------------------------------------

/** 解析文件列表 HTML，返回 FileInfo 列表 */
export function parseFileList(html: string, baseUrl: string): FileInfo[] {
  const files: FileInfo[] = [];
  const $ = cheerio.load(html);
  const grid = $('#GridFiles');
  if (!grid.length) return files;

  grid.find('tr').each((_, row) => {
    const cells = $(row).find('td');
    if (cells.length < 3) return;

    const indexText = $(cells[0]!).text().trim();
    if (!indexText || !indexText.startsWith('[')) return;

    let fileId: number | null = null;
    let title = '';
    let department = '';
    let dateStr = '';
    let isUnread = false;
    let downloadUrl = '';

    const cell2 = $(cells[1]!);
    const link = cell2.find('a').first();
    if (link.length) {
      const href = link.attr('href') ?? '';
      if (href.includes('showfile.aspx')) {
        const m = href.match(/id=(\d+)/);
        if (m) fileId = parseInt(m[1]!, 10);
      }
      title = link.text().trim();
      downloadUrl = new URL(href, baseUrl).href;
    }

    const bold = cell2.find('b').first();
    if (bold.length) {
      department = bold.text().trim().replace(/:$/, '');
    }

    if (cell2.text().includes('未读')) isUnread = true;

    if (cells.length > 3) {
      const dateText = $(cells[3]!).text();
      const dateMatch = dateText.match(/(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日/);
      if (dateMatch) {
        dateStr = `${dateMatch[1]!}-${dateMatch[2]!.padStart(2, '0')}-${dateMatch[3]!.padStart(2, '0')}`;
      }
    }

    files.push({
      id: fileId,
      index: indexText.replace(/^\[|\]$/g, ''),
      title,
      department,
      date: dateStr,
      isUnread,
      detailUrl: downloadUrl,
    });
  });

  return files;
}

/** 从文件列表 HTML 提取分页信息 */
export function parsePaginationInfo(html: string): PaginationInfo {
  const m = html.match(/第(\d+)页\/总(\d+)\s*页\s*每页(\d+)条\/共(\d+)条/);
  if (m) {
    return {
      currentPage: parseInt(m[1]!, 10),
      totalPages: parseInt(m[2]!, 10),
      perPage: parseInt(m[3]!, 10),
      totalItems: parseInt(m[4]!, 10),
    };
  }
  return { currentPage: 1, totalPages: 1, perPage: 50, totalItems: 0 };
}

/** 解析部门列表 */
export function parseDepartments(html: string, wjxtUiUrl: string): DepartmentInfo[] {
  const re = /Right\.aspx\?id=(\d+)&type=(\d+)&tn=([^"'\s]+)/gi;
  const depts: DepartmentInfo[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    depts.push({
      id: parseInt(m[1]!, 10),
      type: parseInt(m[2]!, 10),
      tnEncoded: m[3]!,
      tnDecoded: decodeGb2312(m[3]!),
      url: `${wjxtUiUrl}/Right.aspx?id=${m[1]!}&type=${m[2]!}&tn=${m[3]!}`,
    });
  }

  // 去重
  const seen = new Set<number>();
  return depts.filter(d => {
    if (seen.has(d.id)) return false;
    seen.add(d.id);
    return true;
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/_base.ts
git commit -m "feat(node): add file list and department parsing"
```

---

### Task 11: Implement _base.ts (Part 3 — remaining parsing functions)

**Files:**
- Modify: `packages/node/src/_base.ts` (append remaining functions)

- [ ] **Step 1: Append to _base.ts — parsePhoneList, parseBusinessPage, parseSearchResults, file helpers**

```typescript
// ---------------------------------------------------------------------------
// 电话簿解析
// ---------------------------------------------------------------------------

/** 解析电话簿 HTML */
export function parsePhoneList(html: string): PhoneContact[] {
  const $ = cheerio.load(html);
  const contacts: PhoneContact[] = [];

  $('table').each((_, table) => {
    $(table).find('tr').each((__, row) => {
      const cells = $(row).find('td');
      if (cells.length >= 2) {
        const textCells = cells
          .map((_, c) => $(c).text().trim())
          .get()
          .filter(t => t && t !== '\xa0');
        if (textCells.length >= 2) {
          contacts.push({
            name: textCells[0] ?? '',
            phone: textCells[1] ?? '',
            extra: textCells.slice(2).join(' | '),
          });
        }
      }
    });
  });

  return contacts;
}

// ---------------------------------------------------------------------------
// 业务办理页面解析
// ---------------------------------------------------------------------------

/** 解析业务办理页面 */
export function parseBusinessPage(html: string, pageType: string): BusinessPage {
  const navLinks: Record<string, string> = {};
  let activeTab = '';

  // 提取导航标签
  const linkRe = /<a[^>]*href="(business_[^"]+\.aspx)"[^>]*>(?:<b>)?(?:<strong>)?([^<]*)(?:<\/strong>)?(?:<\/b>)?<\/a>/gi;
  let lm: RegExpExecArray | null;
  while ((lm = linkRe.exec(html)) !== null) {
    navLinks[lm[2]!.trim()] = lm[1]!;
  }

  // 检测激活标签
  const activeRe = /<a[^>]*href="([^"]*)"[^>]*>\s*(?:<b>)?<strong>([^<]*)<\/strong>(?:<\/b>)?\s*<\/a>/i;
  const am = html.match(activeRe);
  if (am) activeTab = am[2]!.trim();

  // 提取 GridView 数据行
  const $ = cheerio.load(html);
  const records: BusinessRecord[] = [];
  const grid = $('#gvList1');
  if (grid.length) {
    grid.find('tr').each((_, row) => {
      const cellTexts = $(row).find('td, th')
        .map((__, c) => $(c).text().trim())
        .get()
        .filter(Boolean);
      if (cellTexts.length) {
        records.push({ rowIndex: records.length, cells: cellTexts });
      }
    });
  }

  // 记录总数
  const countMatch = html.match(/共(\d+)条/);
  const totalCount = countMatch ? parseInt(countMatch[1]!, 10) : 0;

  const hasSearch = html.includes('TextBox1') && html.includes('mysearch');

  return {
    pageType,
    activeTab,
    navLinks,
    records,
    totalCount,
    hasSearch,
    rawHtml: html,
  };
}

// ---------------------------------------------------------------------------
// 搜索结果解析
// ---------------------------------------------------------------------------

/** 解析搜索结果页的 GridFiles */
export function parseSearchResults(html: string, baseUrl: string): FileInfo[] {
  const files: FileInfo[] = [];
  const $ = cheerio.load(html);
  const grid = $('#GridFiles');
  if (!grid.length) return files;

  grid.find('tr').each((_, row) => {
    const cells = $(row).find('td');
    if (cells.length < 3) return;

    const indexCell = $(cells[0]!).text().trim();
    if (!indexCell || !indexCell.startsWith('[')) return;

    let fileId: number | null = null;
    let title = '';
    let department = '';
    let dateStr = '';
    let isUnread = false;

    const contentCell = $(cells[1]!);
    const link = contentCell.find('a').first();
    if (link.length) {
      const href = link.attr('href') ?? '';
      const m = href.match(/id=(\d+)/);
      if (m) fileId = parseInt(m[1]!, 10);
      title = link.text().trim();
    }

    const bold = contentCell.find('b').first();
    if (bold.length) department = bold.text().trim().replace(/:$/, '');

    if (contentCell.text().includes('未读')) isUnread = true;

    if (cells.length > 3) {
      const dateMatch = $(cells[3]!).text().match(/(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日/);
      if (dateMatch) {
        dateStr = `${dateMatch[1]!}-${dateMatch[2]!.padStart(2, '0')}-${dateMatch[3]!.padStart(2, '0')}`;
      }
    }

    files.push({
      id: fileId,
      index: indexCell.replace(/^\[|\]$/g, ''),
      title,
      department,
      date: dateStr,
      isUnread,
      detailUrl: fileId ? `${baseUrl}/showfile.aspx?id=${fileId}` : '',
    });
  });

  return files;
}

/** 提取搜索结果的记录总数 */
export function parseSearchRecordCount(html: string): number {
  const m = html.match(/共(\d+)条/);
  return m ? parseInt(m[1]!, 10) : 0;
}

// ---------------------------------------------------------------------------
// 文件工具
// ---------------------------------------------------------------------------

/** 去除文件名中的非法字符 */
export function safeFilename(name: string, maxLen: number = 120): string {
  let clean = '';
  for (const ch of name) {
    if ('<>:"/\\|?*'.includes(ch)) clean += '_';
    else if ('\r\n\t'.includes(ch)) continue;
    else clean += ch;
  }
  clean = clean.replace(/^[. ]+/, '');
  if (!clean) clean = 'unnamed';
  return clean.slice(0, maxLen);
}

/** 生成文件唯一标识 */
export function fileHash(fileId: number | null): string {
  return crypto.createHash('md5').update(`wjxt_file_${fileId ?? 0}`).digest('hex');
}

/** 解析文件详情页 */
export function parseFileDetail(
  html: string,
  fileId: number,
  detailUrl: string,
  baseUrl: string,
): { fileId: number; title: string; detailUrl: string; rawHtml: string; downloadUrls: Attachment[] } {
  const attachments: Attachment[] = [];

  let title = '';
  const titleMatch = html.match(/document\.title\s*=\s*'([^']*)'/);
  if (titleMatch) title = titleMatch[1]!;

  const seen = new Set<string>();
  const re = /<a[^>]*href="(\/filezip\/uploadfile\/[^"]*)"[^>]*>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    const fullUrl = baseUrl + m[1]!;
    if (seen.has(fullUrl)) continue;
    seen.add(fullUrl);

    const tag = m[0]!;
    const dlName = tag.match(/download="([^"]*)"/);
    const filename = dlName ? dlName[1]! : m[1]!.split('/').pop()!;
    attachments.push({ url: fullUrl, filename });
  }

  return {
    fileId,
    title,
    detailUrl,
    rawHtml: html,
    downloadUrls: attachments,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/_base.ts
git commit -m "feat(node): add phone list, business page, and search result parsing"
```

---

### Task 12: Implement client.ts

**Files:**
- Create: `packages/node/src/client.ts`

- [ ] **Step 1: Write packages/node/src/client.ts**

Since this is the largest file (~500 lines), write it in one step:

```typescript
/**
 * HTTP 客户端 — 广西大学文件管理系统
 * Python 对应: client.py (WjxtClient) + async_client.py (AsyncWjxtClient)
 *
 * 适配说明:
 * - Node.js 没有同步 HTTP 客户端的概念，所有 I/O 操作返回 Promise。
 *   本模块合并 Python 的 WjxtClient 和 AsyncWjxtClient 为单一 async 类。
 * - httpx.Client 自动管理 cookie，Node.js fetch 不管理。
 *   这里手动维护 cookie jar (Map<string, string>)，每次请求传递 Cookie 头。
 * - _check_session 的重试逻辑用闭包实现：保存请求参数，重连后重新 fetch，
 *   对应 Python 的递归调用 _get/_post。
 */

import * as path from 'node:path';
import * as fs from 'node:fs/promises';
import { WjxtConfig } from './config';
import { AuthError, NetworkError, SessionExpiredError } from './exceptions';
import type {
  FileInfo, FileDetail, DepartmentInfo, PhoneContact,
  PaginationInfo, SearchParams, SearchResult, BusinessPage,
} from './types';
import {
  extractViewstate, extractHiddenFields,
  encodeGb2312, encodePostDataGb2312,
  isSessionExpired,
  parseFileList, parsePaginationInfo, parseDepartments,
  parsePhoneList, parseBusinessPage,
  parseSearchResults, parseSearchRecordCount,
  parseFileDetail,
} from './_base';

export class WjxtClient {
  private _config: WjxtConfig;
  private _cookies: Map<string, string> = new Map();
  private _loggedIn = false;
  private _controller = new AbortController();

  constructor(opts?: { username?: string; password?: string; config?: WjxtConfig }) {
    this._config = opts?.config ?? WjxtConfig.fromEnv();
    if (opts?.username) this._config = this._config.mergeWith({ username: opts.username });
    if (opts?.password) this._config = this._config.mergeWith({ password: opts.password });
  }

  // ===== 属性 =====

  get baseUrl(): string { return this._config.baseUrl; }
  get wjxtUi(): string { return `${this._config.baseUrl}/Wjxt_UI`; }
  get loggedIn(): boolean { return this._loggedIn; }

  // ===== 内部 HTTP 方法 =====

  private _cookieHeader(): string {
    return Array.from(this._cookies.entries())
      .map(([k, v]) => `${k}=${v}`).join('; ');
  }

  private _saveCookies(headers: Headers): void {
    const setCookie = headers.get('set-cookie');
    if (!setCookie) return;
    // 只解析简单的 name=value 键值对（ASP.NET 的 cookie 较简单）
    for (const part of setCookie.split(',')) {
      const trimmed = part.trim();
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx === -1) continue;
      const semiIdx = trimmed.indexOf(';');
      const endIdx = semiIdx === -1 ? trimmed.length : semiIdx;
      const name = trimmed.slice(0, eqIdx);
      const value = trimmed.slice(eqIdx + 1, endIdx);
      if (name === 'path' || name === 'expires' || name === 'HttpOnly') continue;
      this._cookies.set(name, value);
    }
  }

  private async _fetch(url: string, init: RequestInit = {}): Promise<string> {
    const headers = new Headers(init.headers);
    const cookieStr = this._cookieHeader();
    if (cookieStr) headers.set('Cookie', cookieStr);
    headers.set('User-Agent', this._config.userAgent);

    const resp = await fetch(url, {
      ...init,
      headers,
      signal: AbortSignal.any([
        this._controller.signal,
        AbortSignal.timeout(this._config.timeout),
      ]),
    });

    this._saveCookies(resp.headers);

    // 读取响应体为 Buffer，用 iconv-lite 解码
    // Node.js 内置 fetch 返回 web Response，通过 arrayBuffer 读取
    const buf = Buffer.from(await resp.arrayBuffer());
    const { default: iconv } = await import('iconv-lite');
    return iconv.decode(buf, 'gb2312');
  }

  private async _get(url: string, opts: RequestInit = {}): Promise<string> {
    try {
      const html = await this._fetch(url, { ...opts, method: 'GET' });
      return await this._checkSession(html, () => this._fetch(url, { ...opts, method: 'GET' }));
    } catch (e) {
      if (e instanceof NetworkError) throw e;
      throw new NetworkError(`GET ${url} 失败: ${(e as Error).message}`, e as Error);
    }
  }

  private async _post(
    url: string, body?: URLSearchParams | string, opts: RequestInit = {}
  ): Promise<string> {
    const headers = new Headers(opts.headers);
    if (body instanceof URLSearchParams) {
      headers.set('Content-Type', 'application/x-www-form-urlencoded');
    }
    const init: RequestInit = { ...opts, method: 'POST', headers };
    if (body) init.body = body instanceof URLSearchParams ? body.toString() : body;

    try {
      const html = await this._fetch(url, init);
      return await this._checkSession(html, () => this._fetch(url, init));
    } catch (e) {
      if (e instanceof NetworkError) throw e;
      throw new NetworkError(`POST ${url} 失败: ${(e as Error).message}`, e as Error);
    }
  }

  /**
   * 检测会话过期并自动重连，最多重试一次
   *
   * retryFn 是闭包：保存了原始请求的全部参数，重连后直接调用。
   * 对应 Python 的 _check_session 方法，但用闭包避免了递归。
   */
  private async _checkSession(html: string, retryFn: () => Promise<string>): Promise<string> {
    if (!isSessionExpired(html)) return html;

    if (!this._config.autoRelogin) {
      throw new SessionExpiredError('会话已过期，auto_relogin 已禁用');
    }

    this._loggedIn = false;
    await this.login();

    const html2 = await retryFn();
    if (isSessionExpired(html2)) {
      throw new SessionExpiredError('会话已过期，自动重连后仍然失败，请检查账号状态');
    }
    return html2;
  }

  /** 确保已登录，未登录时自动调用 login() */
  private async _ensureLoggedIn(): Promise<void> {
    if (!this._loggedIn) await this.login();
  }

  /** 关闭客户端（取消所有进行中的请求） */
  close(): void {
    this._controller.abort();
    this._controller = new AbortController();
  }

  /** TypeScript 5.2+ using 语法支持 */
  [Symbol.dispose](): void {
    this.close();
  }

  // ===== 1. 认证 =====

  async login(): Promise<boolean> {
    try {
      const html = await this._get(`${this.baseUrl}/Login.aspx`);
      const fields = extractViewstate(html);

      fields['userIdCard'] = this._config.username;
      fields['userPwd'] = this._config.password;
      fields['loginsubmit'] = '登 录';
      fields['myteip'] = this._config.myteip;

      const params = new URLSearchParams(fields);
      const html2 = await this._post(`${this.baseUrl}/default.aspx`, params);

      if (html2.includes('Wjxt_UI') || html2.toLowerCase().includes('window.open')) {
        this._loggedIn = true;
        return true;
      }

      this._loggedIn = !html2.includes('userIdCard') && html2.length < 5000;
      return this._loggedIn;
    } catch (e) {
      if (e instanceof NetworkError) throw e;
      throw new AuthError(`登录失败: ${(e as Error).message}`, e as Error);
    }
  }

  async logout(): Promise<boolean> {
    await this._ensureLoggedIn();
    const html = await this._get(
      `${this.wjxtUi}/Exiting.aspx`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } },
    );
    this._loggedIn = false;
    return true; // Respone 200 等价
  }

  // ===== 2. 主页 & 导航 =====

  async getMainPage(): Promise<string> {
    await this._ensureLoggedIn();
    return this._get(`${this.wjxtUi}/default.aspx`);
  }

  async getSidebar(): Promise<string> {
    await this._ensureLoggedIn();
    return this._get(
      `${this.wjxtUi}/WebUI.aspx?id=2`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } },
    );
  }

  async getDepartmentList(): Promise<string> {
    await this._ensureLoggedIn();
    return this._get(
      `${this.wjxtUi}/WebUI.aspx?id=4`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } },
    );
  }

  async getDepartments(): Promise<DepartmentInfo[]> {
    const html = await this.getDepartmentList();
    return parseDepartments(html, this.wjxtUi);
  }

  // ===== 3. 文件列表 =====

  private async _setupListContext(): Promise<void> {
    await this._get(`${this.wjxtUi}/default.aspx`);
    await this._get(
      `${this.wjxtUi}/WebUI.aspx?id=4`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } },
    );
  }

  async getFileList(
    listId: number = 127, listType: number = 100,
    listName: string = '全部文件', page: number = 1,
  ): Promise<string> {
    await this._ensureLoggedIn();

    const tnEncoded = encodeGb2312(listName);
    const baseUrl = `${this.wjxtUi}/PageList.aspx?id=${listId}&type=${listType}&tn=${tnEncoded}`;

    await this._setupListContext();

    if (page <= 1) {
      return this._get(baseUrl,
        { headers: { Referer: `${this.wjxtUi}/WebUI.aspx?id=4` } });
    }

    const html1 = await this._get(baseUrl);
    const fields = extractViewstate(html1);
    fields['__EVENTTARGET'] = 'AspNetPager1';
    fields['__EVENTARGUMENT'] = String(page);

    return this._post(baseUrl, new URLSearchParams(fields),
      { headers: { Referer: baseUrl } });
  }

  async getDeptFiles(
    deptId: number, deptType: number = 0,
    deptName: string = '', page: number = 1,
  ): Promise<string> {
    await this._ensureLoggedIn();

    const tnEncoded = encodeGb2312(deptName);
    const baseUrl = `${this.wjxtUi}/Right.aspx?id=${deptId}&type=${deptType}&tn=${tnEncoded}`;

    await this._setupListContext();

    if (page <= 1) return this._get(baseUrl);

    const html1 = await this._get(baseUrl);
    const fields = extractViewstate(html1);
    fields['__EVENTTARGET'] = 'AspNetPager1';
    fields['__EVENTARGUMENT'] = String(page);

    return this._post(baseUrl, new URLSearchParams(fields),
      { headers: { Referer: baseUrl } });
  }

  // ===== 3b. 文件列表生成器 =====

  /** 惰性遍历全部文件列表（AsyncGenerator 对应 Python Iterator） */
  async *iterFiles(maxPages?: number): AsyncGenerator<FileInfo> {
    const html = await this.getFileList(127, 100, '全部文件', 1);
    const pageInfo = parsePaginationInfo(html);
    for (const f of parseFileList(html, this.wjxtUi)) yield f;

    let totalPages = pageInfo.totalPages;
    if (maxPages) totalPages = Math.min(totalPages, maxPages);

    for (let p = 2; p <= totalPages; p++) {
      await this._delay(this._config.pageDelay);
      const nextHtml = await this.getFileList(127, 100, '全部文件', p);
      for (const f of parseFileList(nextHtml, this.wjxtUi)) yield f;
    }
  }

  /** 惰性遍历部门文件列表 */
  async *iterDeptFiles(
    deptId: number, deptName: string = '', maxPages?: number,
  ): AsyncGenerator<FileInfo> {
    const html = await this.getDeptFiles(deptId, 0, deptName, 1);
    const pageInfo = parsePaginationInfo(html);
    for (const f of parseFileList(html, this.wjxtUi)) yield f;

    let totalPages = pageInfo.totalPages;
    if (maxPages) totalPages = Math.min(totalPages, maxPages);

    for (let p = 2; p <= totalPages; p++) {
      await this._delay(this._config.pageDelay);
      const nextHtml = await this.getDeptFiles(deptId, 0, deptName, p);
      for (const f of parseFileList(nextHtml, this.wjxtUi)) yield f;
    }
  }

  async getFileListStructured(page: number = 1): Promise<[FileInfo[], PaginationInfo]> {
    const html = await this.getFileList(127, 100, '全部文件', page);
    return [parseFileList(html, this.wjxtUi), parsePaginationInfo(html)];
  }

  // ===== 4. 文件详情 & 下载 =====

  async getFileDetail(fileId: number): Promise<FileDetail> {
    await this._ensureLoggedIn();

    await this._get(`${this.wjxtUi}/default.aspx`);
    await this._get(`${this.wjxtUi}/qstwj.aspx`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } });

    const url = `${this.wjxtUi}/showfile.aspx?id=${fileId}`;
    const html = await this._get(url,
      { headers: { Referer: `${this.wjxtUi}/qstwj.aspx` } });

    const detail = parseFileDetail(html, fileId, url, this.baseUrl);
    return {
      fileId: detail.fileId,
      title: detail.title,
      detailUrl: detail.detailUrl,
      rawHtml: detail.rawHtml,
      downloadUrls: detail.downloadUrls,
    };
  }

  async downloadFile(opts: {
    fileId?: number; url?: string; saveDir?: string;
  } = {}): Promise<string | null> {
    await this._ensureLoggedIn();

    let downloadUrl = opts.url ?? null;
    if (opts.fileId) {
      const detail = await this.getFileDetail(opts.fileId);
      if (detail.downloadUrls.length === 0) return null;
      downloadUrl = detail.downloadUrls[0]!.url;
    }
    if (!downloadUrl) return null;

    if (downloadUrl.startsWith('/')) {
      downloadUrl = this.baseUrl + downloadUrl;
    }

    const html = await this._get(downloadUrl,
      { headers: { Referer: `${this.wjxtUi}/showfile.aspx` } });

    // downloadFile 返回的是二进制内容，不能走 _get（它解码为字符串）
    // 需要单独处理下载请求
    const saveDir = opts.saveDir ?? '.';
    const filename = path.basename(new URL(downloadUrl).pathname.split('?')[0]!);
    const filepath = path.join(saveDir, filename);

    // 用原始 fetch 下载（不走 _get 的文本解码流程）
    const resp = await fetch(downloadUrl, {
      headers: {
        Cookie: this._cookieHeader(),
        'User-Agent': this._config.userAgent,
        Referer: `${this.wjxtUi}/showfile.aspx`,
      },
      signal: AbortSignal.timeout(this._config.timeout),
    });
    const buf = Buffer.from(await resp.arrayBuffer());
    await fs.writeFile(filepath, buf);
    return filepath;
  }

  // ===== 5. 搜索 =====

  private async _getSearchViewstate(): Promise<Record<string, string>> {
    await this._get(`${this.wjxtUi}/default.aspx`);
    const html = await this._get(`${this.wjxtUi}/WebUI.aspx?id=2`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } });
    return { ...extractViewstate(html), ...extractHiddenFields(html) };
  }

  /** POST 搜索请求（GB2312 编码，含会话自动恢复） */
  private async _searchPost(url: string, fields: Record<string, string>): Promise<string> {
    const body = encodePostDataGb2312(fields);
    const getHeaders = (): Record<string, string> => ({
      'Content-Type': 'application/x-www-form-urlencoded',
      Referer: `${this.wjxtUi}/WebUI.aspx?id=2`,
    });

    const doRequest = async (): Promise<string> => {
      const headers = new Headers(getHeaders());
      const cookieStr = this._cookieHeader();
      if (cookieStr) headers.set('Cookie', cookieStr);
      headers.set('User-Agent', this._config.userAgent);

      const resp = await fetch(url, {
        method: 'POST',
        headers,
        body,
        signal: AbortSignal.timeout(this._config.timeout),
      });
      this._saveCookies(resp.headers);
      const buf = Buffer.from(await resp.arrayBuffer());
      const { default: iconv } = await import('iconv-lite');
      return iconv.decode(buf, 'gbk');
    };

    try {
      let html = await doRequest();
      if (isSessionExpired(html)) {
        if (!this._config.autoRelogin) throw new SessionExpiredError('会话已过期');
        this._loggedIn = false;
        await this.login();
        html = await doRequest();
        if (isSessionExpired(html)) {
          throw new SessionExpiredError('会话已过期，自动重连后仍然失败');
        }
      }
      return html;
    } catch (e) {
      if (e instanceof NetworkError || e instanceof SessionExpiredError) throw e;
      throw new NetworkError(`POST ${url} 失败: ${(e as Error).message}`, e as Error);
    }
  }

  async search(params?: SearchParams, page: number = 1): Promise<SearchResult> {
    const p = params ?? { keyword: '', searchType: 'title', fileType: '全部文件', fileYear: '0', matchMode: 'Fuzzy' };
    await this._ensureLoggedIn();

    const fields = await this._getSearchViewstate();
    fields['content'] = p.keyword;
    fields['searchType'] = p.searchType;
    fields['filetype'] = p.fileType;
    fields['fileTime'] = p.fileYear;
    fields['AccurateFuzzy'] = p.matchMode;

    const searchUrl = `${this.wjxtUi}/search.aspx`;
    let html: string;

    if (page <= 1) {
      fields['__EVENTTARGET'] = 'Button1';
      fields['__EVENTARGUMENT'] = '';
      html = await this._searchPost(searchUrl, fields);
    } else {
      fields['__EVENTTARGET'] = 'Button1';
      fields['__EVENTARGUMENT'] = '';
      const htmlP1 = await this._searchPost(searchUrl, { ...fields });
      const vs = { ...extractViewstate(htmlP1), ...extractHiddenFields(htmlP1) };
      vs['__EVENTTARGET'] = 'AspNetPager1';
      vs['__EVENTARGUMENT'] = String(page);

      const params2 = new URLSearchParams(vs);
      html = await this._post(searchUrl, params2,
        { headers: { Referer: searchUrl } });
    }

    const files = parseSearchResults(html, this.wjxtUi);
    const totalCount = parseSearchRecordCount(html);
    const perPage = 50;
    const totalPages = Math.max(1, Math.ceil(totalCount / perPage));

    return { files, totalCount, currentPage: page, totalPages, perPage };
  }

  /** 惰性搜索遍历全部结果 */
  async *iterSearch(params?: SearchParams, maxPages?: number): AsyncGenerator<FileInfo> {
    const result = await this.search(params, 1);
    for (const f of result.files) yield f;

    let totalPages = result.totalPages;
    if (maxPages) totalPages = Math.min(totalPages, maxPages);

    for (let p = 2; p <= totalPages; p++) {
      await this._delay(this._config.pageDelay);
      const pageResult = await this.search(params, p);
      for (const f of pageResult.files) yield f;
    }
  }

  // ===== 6. 用户管理 =====

  async changePassword(oldPwd: string, newPwd: string): Promise<boolean> {
    await this._ensureLoggedIn();

    const html1 = await this._get(`${this.wjxtUi}/userEditPss.aspx`);
    const fields = { ...extractViewstate(html1), ...extractHiddenFields(html1) };
    fields['oldPwd'] = oldPwd;
    fields['userPWD1'] = newPwd;
    fields['userPWD2'] = newPwd;

    const html2 = await this._post(
      `${this.wjxtUi}/userEditPss.aspx`,
      new URLSearchParams(fields),
      { headers: { Referer: `${this.wjxtUi}/userEditPss.aspx` } },
    );

    return html2.includes('成功') || html2.includes('修改成功');
  }

  // ===== 7. 电话簿 =====

  async getPhoneList(): Promise<string> {
    await this._ensureLoggedIn();
    await this._get(`${this.wjxtUi}/default.aspx`);
    return this._get(`${this.wjxtUi}/phoneList.aspx`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } });
  }

  async parsePhoneList(html?: string): Promise<PhoneContact[]> {
    const h = html ?? await this.getPhoneList();
    return parsePhoneList(h);
  }

  // ===== 8. 业务办理 =====

  async getTodoList(): Promise<BusinessPage> {
    await this._ensureLoggedIn();
    const html = await this._get(
      `${this.baseUrl}/business/business_mytodolists.aspx`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } },
    );
    return parseBusinessPage(html, 'mytodolists');
  }

  async getTodoProcessing(): Promise<BusinessPage> {
    await this._ensureLoggedIn();
    const html = await this._get(
      `${this.baseUrl}/business/business_DoList.aspx`,
      { headers: { Referer: `${this.baseUrl}/business/business_mytodolists.aspx` } },
    );
    return parseBusinessPage(html, 'do_list');
  }

  async getMyTodoLists(): Promise<BusinessPage> {
    await this._ensureLoggedIn();
    const html = await this._get(
      `${this.baseUrl}/business/business_MyToDoLists.aspx`,
      { headers: { Referer: `${this.baseUrl}/business/business_mytodolists.aspx` } },
    );
    return parseBusinessPage(html, 'my_todo_lists');
  }

  async getMyUpdateLists(): Promise<BusinessPage> {
    await this._ensureLoggedIn();
    const html = await this._get(
      `${this.baseUrl}/business/business_MyUpLists.aspx`,
      { headers: { Referer: `${this.baseUrl}/business/business_mytodolists.aspx` } },
    );
    return parseBusinessPage(html, 'my_up_lists');
  }

  async getBusinessAddPage(): Promise<BusinessPage> {
    await this._ensureLoggedIn();
    const html = await this._get(
      `${this.baseUrl}/business/businessAdd.aspx`,
      { headers: { Referer: `${this.baseUrl}/business/business_mytodolists.aspx` } },
    );
    return parseBusinessPage(html, 'add');
  }

  async addBusiness(formData: Record<string, string>): Promise<string> {
    await this._ensureLoggedIn();

    const html1 = await this._get(`${this.baseUrl}/business/businessAdd.aspx`);
    const fields = { ...extractViewstate(html1), ...extractHiddenFields(html1), ...formData };

    return this._post(
      `${this.baseUrl}/business/businessAdd.aspx`,
      new URLSearchParams(fields),
      { headers: { Referer: `${this.baseUrl}/business/businessAdd.aspx` } },
    );
  }

  // ===== 工具 =====

  private _delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/client.ts
git commit -m "feat(node): add HTTP client with full API coverage"
```

---

### Task 13: Implement crawler.ts

**Files:**
- Create: `packages/node/src/crawler.ts`

- [ ] **Step 1: Write packages/node/src/crawler.ts**

```typescript
/**
 * 文件下载爬虫
 * Python 对应: crawler.py (FileCrawler)
 *
 * 适配说明:
 * - ThreadPoolExecutor → Promise 并发 + 信号量控制并发数
 * - threading.Lock → 不需要（Node.js 单线程，无竞态条件）
 * - time.sleep(sec) → await delay(ms)，单位秒→毫秒
 * - concurrent.futures.as_completed → Promise.allSettled
 */

import * as path from 'node:path';
import { readFileSync } from 'node:fs';
import * as fs from 'node:fs/promises';
import { WjxtClient } from './client';
import {
  parseFileList, parsePaginationInfo,
  fileHash, safeFilename,
} from './_base';
import { DownloadError } from './exceptions';
import type { FileInfo, CrawlStats, CrawlOptions } from './types';
import { createCrawlStats } from './types';

export class FileCrawler {
  private client: WjxtClient;
  private downloadDir: string;
  private concurrency: number;
  private pageDelay: number;
  private historyPath: string;
  private _history: Set<string>;

  constructor(client: WjxtClient, opts?: {
    downloadDir?: string; concurrency?: number; pageDelay?: number;
  }) {
    this.client = client;
    this.downloadDir = path.resolve(opts?.downloadDir ?? './downloads');
    this.concurrency = opts?.concurrency ?? 1;
    this.pageDelay = opts?.pageDelay ?? 500;
    this.historyPath = path.join(this.downloadDir, 'download_history.json');
    this._history = this._loadHistory();
  }

  get history(): Set<string> { return this._history; }

  // ===== 下载记录 =====

  private _loadHistory(): Set<string> {
    try {
      // 同步读（首次加载时还未有异步上下文）
      const data = JSON.parse(readFileSync(this.historyPath, 'utf-8'));
      return new Set(data.downloaded ?? []);
    } catch {
      return new Set();
    }
  }

  private async _saveHistory(): Promise<void> {
    await fs.mkdir(path.dirname(this.historyPath), { recursive: true });
    const data = {
      updated: new Date().toISOString(),
      count: this._history.size,
      downloaded: [...this._history].sort(),
    };
    await fs.writeFile(this.historyPath, JSON.stringify(data, null, 2), 'utf-8');
  }

  clearHistory(): void {
    this._history.clear();
    // 异步删除但不需要等待
    fs.unlink(this.historyPath).catch(() => {});
  }

  // ===== 过滤 =====

  static filterFiles(files: FileInfo[], opts?: {
    after?: Date; unreadOnly?: boolean;
  }): FileInfo[] {
    return files.filter(f => {
      if (opts?.unreadOnly && !f.isUnread) return false;
      if (opts?.after && f.date) {
        const d = new Date(f.date);
        if (!isNaN(d.getTime()) && d < opts.after) return false;
      }
      return true;
    });
  }

  // ===== 单文件下载 =====

  async downloadOne(fileInfo: FileInfo, dryRun: boolean = false): Promise<string | null> {
    const fileId = fileInfo.id;
    if (!fileId) return null;

    const fhash = fileHash(fileId);
    if (this._history.has(fhash)) return null;

    // 获取详情（带重试）
    let detail;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        detail = await this.client.getFileDetail(fileId);
        if (detail?.rawHtml) break;
      } catch { /* retry */ }
      if (attempt < 2) await this._delay(2000);
    }

    if (!detail?.rawHtml) return null;

    const attachments = detail.downloadUrls;

    // 构建目录
    const dept = safeFilename(fileInfo.department || '广西大学', 40);
    const dateStr = fileInfo.date || '0000-00-00';
    const title = safeFilename(fileInfo.title || '无标题', 80);
    const fileDirName = safeFilename(`${dateStr}_${title}`, 100);
    const fileDir = path.join(this.downloadDir, dept, fileDirName);

    if (dryRun) {
      const tag = attachments.length ? `${attachments.length} 个附件` : '仅 HTML';
      console.log(`  [DRY-RUN] ${dept}/${fileDirName}/ (${tag})`);
      for (const att of attachments) {
        console.log(`    -> ${att.filename}`);
      }
      this._history.add(fhash);
      await this._saveHistory();
      return fileDir;
    }

    await fs.mkdir(fileDir, { recursive: true });

    // 保存 HTML 正文
    const htmlFilename = safeFilename(`${dateStr}_${title}.html`, 120);
    const htmlPath = path.join(fileDir, htmlFilename);
    try {
      await fs.access(htmlPath);
    } catch {
      await fs.writeFile(htmlPath, detail.rawHtml, 'utf-8');
    }

    // 下载附件
    for (const att of attachments) {
      const attFilename = safeFilename(att.filename);
      const attPath = path.join(fileDir, attFilename);

      try {
        await fs.access(attPath);
        continue; // 已存在
      } catch { /* 需要下载 */ }

      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const url = att.url.startsWith('/') ? this.client.baseUrl + att.url : att.url;
          const resp = await fetch(url, {
            signal: AbortSignal.timeout(30_000),
          });
          const buf = Buffer.from(await resp.arrayBuffer());
          await fs.writeFile(attPath, buf);
          break;
        } catch {
          if (attempt < 2) await this._delay(2000);
        }
      }
    }

    this._history.add(fhash);
    await this._saveHistory();
    return fileDir;
  }

  // ===== 批量下载（信号量控制并发） =====

  async downloadBatch(files: FileInfo[], dryRun: boolean = false): Promise<CrawlStats> {
    const stats = createCrawlStats();
    stats.totalFiles = files.length;
    if (files.length === 0) return stats;

    if (this.concurrency <= 1) {
      for (let i = 0; i < files.length; i++) {
        const f = files[i]!;
        const fhash = fileHash(f.id);

        if (fhash && this._history.has(fhash)) {
          stats.skipped++;
        } else if (!f.id) {
          stats.noAttachment++;
        } else {
          const result = await this.downloadOne(f, dryRun);
          if (result) stats.downloaded++;
          else stats.failed++;
        }

        const bar = FileCrawler._progressBar(i + 1, files.length);
        process.stdout.write(`\r${bar}`);
      }
      process.stdout.write('\n');
    } else {
      // 并发控制：信号量模式
      let done = 0;
      const semaphore = new Array<Promise<void>>(this.concurrency).fill(Promise.resolve());

      for (const f of files) {
        const fhash = fileHash(f.id);

        if (fhash && this._history.has(fhash)) {
          stats.skipped++;
          done++;
          continue;
        }
        if (!f.id) {
          stats.noAttachment++;
          done++;
          continue;
        }

        const worker = async () => {
          const result = await this.downloadOne(f, dryRun);
          if (result) stats.downloaded++;
          else stats.failed++;
          done++;
          const bar = FileCrawler._progressBar(done, files.length);
          process.stdout.write(`\r${bar}`);
        };

        // Race to claim next available slot
        await Promise.race(semaphore.map(async (p, i) => {
          await p;
          semaphore[i] = worker();
        }));
      }

      await Promise.all(semaphore);
      process.stdout.write('\n');
    }

    return stats;
  }

  // ===== 爬取策略 =====

  async crawlAll(opts: CrawlOptions = {}): Promise<CrawlStats> {
    const allStats = createCrawlStats();
    const maxEmptyPages = opts.maxEmptyPages ?? 3;

    const html1 = await this.client.getFileList(127, 100, '全部文件', 1);
    const pageInfo = parsePaginationInfo(html1);
    let files = parseFileList(html1, this.client.wjxtUi);

    let totalPages = pageInfo.totalPages;
    if (opts.maxPages) totalPages = Math.min(totalPages, opts.maxPages);

    let filtered = FileCrawler.filterFiles(files, { after: opts.after, unreadOnly: opts.unreadOnly });
    console.log(`\n[全部文件] 第 1/${totalPages} 页, 本页 ${files.length} 条, 符合条件 ${filtered.length} 条`);

    let emptyStreak = filtered.length ? 0 : 1;

    if (filtered.length) {
      const stats = await this.downloadBatch(filtered, opts.dryRun);
      allStats.totalFiles += files.length;
      allStats.downloaded += stats.downloaded;
      allStats.skipped += stats.skipped;
      allStats.noAttachment += stats.noAttachment;
      allStats.failed += stats.failed;
    }

    for (let p = 2; p <= totalPages; p++) {
      await this._delay(this.pageDelay);
      const html = await this.client.getFileList(127, 100, '全部文件', p);
      files = parseFileList(html, this.client.wjxtUi);

      filtered = FileCrawler.filterFiles(files, { after: opts.after, unreadOnly: opts.unreadOnly });
      const pct = Math.round(p / totalPages * 100);
      console.log(`\n第 ${p}/${totalPages} 页 [${pct}%], 本页 ${files.length} 条, 符合条件 ${filtered.length} 条`);

      if (!filtered.length) {
        if (maxEmptyPages > 0) {
          emptyStreak++;
          if (emptyStreak >= maxEmptyPages) {
            console.log(`  连续 ${emptyStreak} 页无匹配记录，停止翻页。`);
            break;
          }
        }
        continue;
      }

      emptyStreak = 0;
      const stats = await this.downloadBatch(filtered, opts.dryRun);
      allStats.totalFiles += files.length;
      allStats.downloaded += stats.downloaded;
      allStats.skipped += stats.skipped;
      allStats.noAttachment += stats.noAttachment;
      allStats.failed += stats.failed;
    }

    return allStats;
  }

  async crawlDepartment(deptId: number, opts: CrawlOptions & { deptName?: string } = {}): Promise<CrawlStats> {
    const allStats = createCrawlStats();
    const maxEmptyPages = opts.maxEmptyPages ?? 3;
    const deptName = opts.deptName ?? '';

    const html1 = await this.client.getDeptFiles(deptId, 0, deptName, 1);
    const pageInfo = parsePaginationInfo(html1);
    let files = parseFileList(html1, this.client.wjxtUi);

    let totalPages = pageInfo.totalPages;
    if (opts.maxPages) totalPages = Math.min(totalPages, opts.maxPages);

    let filtered = FileCrawler.filterFiles(files, { after: opts.after, unreadOnly: opts.unreadOnly });
    console.log(`\n  [${deptId}] ${deptName}`);
    console.log(`  第 1/${totalPages} 页, 本页 ${files.length} 条, 符合条件 ${filtered.length} 条`);

    let emptyStreak = filtered.length ? 0 : 1;

    if (filtered.length) {
      const stats = await this.downloadBatch(filtered, opts.dryRun);
      allStats.totalFiles += files.length;
      allStats.downloaded += stats.downloaded;
      allStats.skipped += stats.skipped;
      allStats.noAttachment += stats.noAttachment;
      allStats.failed += stats.failed;
    }

    for (let p = 2; p <= totalPages; p++) {
      await this._delay(this.pageDelay);
      const html = await this.client.getDeptFiles(deptId, 0, deptName, p);
      files = parseFileList(html, this.client.wjxtUi);

      filtered = FileCrawler.filterFiles(files, { after: opts.after, unreadOnly: opts.unreadOnly });
      const pct = Math.round(p / totalPages * 100);
      console.log(`\n  第 ${p}/${totalPages} 页 [${pct}%], 本页 ${files.length} 条, 符合条件 ${filtered.length} 条`);

      if (!filtered.length) {
        if (maxEmptyPages > 0) {
          emptyStreak++;
          if (emptyStreak >= maxEmptyPages) {
            console.log(`  连续 ${emptyStreak} 页无匹配记录，停止翻页。`);
            break;
          }
        }
        continue;
      }

      emptyStreak = 0;
      const stats = await this.downloadBatch(filtered, opts.dryRun);
      allStats.totalFiles += files.length;
      allStats.downloaded += stats.downloaded;
      allStats.skipped += stats.skipped;
      allStats.noAttachment += stats.noAttachment;
      allStats.failed += stats.failed;
    }

    return allStats;
  }

  async crawlAllDepartments(opts: CrawlOptions = {}): Promise<CrawlStats> {
    const depts = await this.client.getDepartments();
    console.log(`共 ${depts.length} 个部门\n`);

    const allStats = createCrawlStats();
    for (let i = 0; i < depts.length; i++) {
      const d = depts[i]!;
      console.log(`${'='.repeat(50)}`);
      console.log(`部门 [${i + 1}/${depts.length}]`);
      try {
        const stats = await this.crawlDepartment(d.id, { ...opts, deptName: d.tnDecoded });
        allStats.totalFiles += stats.totalFiles;
        allStats.downloaded += stats.downloaded;
        allStats.skipped += stats.skipped;
        allStats.noAttachment += stats.noAttachment;
        allStats.failed += stats.failed;
      } catch (e) {
        console.log(`  [跳过] 部门 [${d.id}] ${d.tnDecoded} 出错: ${(e as Error).message}`);
      }
    }

    return allStats;
  }

  // ===== 工具 =====

  private _delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private static _progressBar(done: number, total: number, width: number = 20): string {
    if (total <= 0) return '';
    const filled = Math.round(width * done / total);
    const bar = '█'.repeat(filled) + '░'.repeat(width - filled);
    const pct = Math.round(done / total * 100);
    return `  [${bar}] ${done}/${total}  ${pct}%`;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/crawler.ts
git commit -m "feat(node): add file download crawler"
```

---

### Task 14: Implement index.ts (public API)

**Files:**
- Create: `packages/node/src/index.ts`

- [ ] **Step 1: Write packages/node/src/index.ts**

```typescript
/**
 * @gxuwjxt/node — 广西大学文件管理系统 Node.js/TypeScript SDK
 *
 * @example
 * ```typescript
 * import { WjxtClient } from '@gxuwjxt/node';
 *
 * const client = new WjxtClient({ username: 'student_id', password: 'password' });
 * await client.login();
 *
 * for await (const file of client.iterFiles({ maxPages: 3 })) {
 *   console.log(file.title);
 * }
 * ```
 */

// 客户端
export { WjxtClient } from './client';

// 爬虫
export { FileCrawler } from './crawler';

// 配置
export { WjxtConfig } from './config';

// 异常
export {
  WjxtError,
  AuthError,
  NetworkError,
  ParseError,
  SessionExpiredError,
  DownloadError,
} from './exceptions';

// 类型
export type {
  FileInfo,
  FileDetail,
  Attachment,
  DepartmentInfo,
  PhoneContact,
  PaginationInfo,
  SearchParams,
  SearchResult,
  BusinessPage,
  BusinessRecord,
  CrawlStats,
  CrawlOptions,
} from './types';

// 工具函数（供高级用法）
export {
  createCrawlStats,
} from './types';
```

- [ ] **Step 2: Commit**

```bash
git add packages/node/src/index.ts
git commit -m "feat(node): add public API index with re-exports"
```

---

### Task 15: Write basic tests

**Files:**
- Create: `packages/node/test/client.test.ts`

- [ ] **Step 1: Write packages/node/test/client.test.ts**

```typescript
import { describe, it, expect } from 'vitest';
import { WjxtConfig } from '../src/config';
import { WjxtError, AuthError, NetworkError, ParseError, SessionExpiredError, DownloadError } from '../src/exceptions';
import { createCrawlStats } from '../src/types';
import {
  encodeGb2312, decodeGb2312,
  extractViewstate, extractHiddenFields,
  isSessionExpired,
  parsePaginationInfo,
  safeFilename, fileHash,
} from '../src/_base';

describe('WjxtConfig', () => {
  it('should create config with defaults', () => {
    const config = new WjxtConfig();
    expect(config.baseUrl).toBe('https://wjxt.gxu.edu.cn');
    expect(config.timeout).toBe(30_000);
    expect(config.autoRelogin).toBe(true);
  });

  it('should merge overrides', () => {
    const config = new WjxtConfig({ username: 'test' });
    const merged = config.mergeWith({ password: 'secret' });
    expect(merged.username).toBe('test');
    expect(merged.password).toBe('secret');
  });
});

describe('Exceptions', () => {
  it('should create WjxtError', () => {
    const err = new WjxtError('test error');
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(WjxtError);
    expect(err.message).toBe('test error');
    expect(err.name).toBe('WjxtError');
  });

  it('should create AuthError with cause', () => {
    const cause = new Error('underlying');
    const err = new AuthError('login failed', cause);
    expect(err).toBeInstanceOf(WjxtError);
    expect(err).toBeInstanceOf(AuthError);
    expect(err.cause).toBe(cause);
  });

  it('should have correct inheritance chain for all exceptions', () => {
    expect(new NetworkError('')).toBeInstanceOf(WjxtError);
    expect(new ParseError('')).toBeInstanceOf(WjxtError);
    expect(new SessionExpiredError('')).toBeInstanceOf(WjxtError);
    expect(new DownloadError('')).toBeInstanceOf(WjxtError);
  });
});

describe('Base utilities', () => {
  it('should encode GB2312', () => {
    const encoded = encodeGb2312('全部文件');
    expect(encoded).toBeTruthy();
    expect(encoded.startsWith('%')).toBe(true);
  });

  it('should decode GB2312 roundtrip', () => {
    const original = '学工部';
    const encoded = encodeGb2312(original);
    const decoded = decodeGb2312(encoded);
    expect(decoded).toBe(original);
  });

  it('should extract VIEWSTATE from ASP.NET HTML', () => {
    const html = '<input type="hidden" name="__VIEWSTATE" value="abc123" />';
    const fields = extractViewstate(html);
    expect(fields['__VIEWSTATE']).toBe('abc123');
  });

  it('should extract hidden fields', () => {
    const html = '<input type="hidden" name="myField" value="myValue" />';
    const fields = extractHiddenFields(html);
    expect(fields['myField']).toBe('myValue');
  });

  it('should detect session expired', () => {
    // 短 HTML 包含过期特征
    const expiredHtml = 'window.location="default.aspx"请重新登录';
    expect(isSessionExpired(expiredHtml)).toBe(true);
  });

  it('should not flag normal HTML as expired', () => {
    const normalHtml = '<html><body>' + 'x'.repeat(1000) + '</body></html>';
    expect(isSessionExpired(normalHtml)).toBe(false);
  });

  it('should parse pagination info', () => {
    const html = '第3页/总10 页 每页50条/共482条';
    const info = parsePaginationInfo(html);
    expect(info.currentPage).toBe(3);
    expect(info.totalPages).toBe(10);
    expect(info.perPage).toBe(50);
    expect(info.totalItems).toBe(482);
  });

  it('should return defaults for missing pagination', () => {
    const info = parsePaginationInfo('no match');
    expect(info.currentPage).toBe(1);
    expect(info.totalPages).toBe(1);
    expect(info.perPage).toBe(50);
    expect(info.totalItems).toBe(0);
  });

  it('should create safe filenames', () => {
    expect(safeFilename('test')).toBe('test');
    expect(safeFilename('a<b>c')).toBe('a_b_c');
    expect(safeFilename('')).toBe('unnamed');
  });

  it('should generate file hash', () => {
    const hash = fileHash(12345);
    expect(hash).toBeTruthy();
    expect(hash).toBe(fileHash(12345)); // deterministic
    expect(hash).not.toBe(fileHash(12346)); // different for different id
  });
});

describe('CrawlStats', () => {
  it('should create zero-initialized stats', () => {
    const stats = createCrawlStats();
    expect(stats.totalFiles).toBe(0);
    expect(stats.downloaded).toBe(0);
    expect(stats.skipped).toBe(0);
    expect(stats.noAttachment).toBe(0);
    expect(stats.failed).toBe(0);
  });
});
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd packages/node && npx vitest run
```

Expected: 14+ tests pass (all pure-logic tests, no network required)

- [ ] **Step 3: Commit**

```bash
git add packages/node/test/client.test.ts
git commit -m "test(node): add unit tests for config, exceptions, and base utilities"
```

---

### Task 16: Build and final verification

**Files:**
- Verify: all files in place

- [ ] **Step 1: Install all workspace dependencies**

```bash
pnpm install
```

Expected: No errors, `packages/node/node_modules` populated

- [ ] **Step 2: Build Node.js SDK**

```bash
pnpm build:node
```

Expected: `packages/node/dist/` created with `index.js`, `index.cjs`, `index.d.ts`

- [ ] **Step 3: Run Node.js tests**

```bash
pnpm test:node
```

Expected: All tests pass

- [ ] **Step 4: Verify Python SDK still works**

```bash
python -c "import sys; sys.path.insert(0, 'packages/python/src'); from gxu_wjxt import WjxtClient, AsyncWjxtClient, FileCrawler, WjxtConfig, WjxtError, AuthError; print('Python SDK OK')"
```

Expected: `Python SDK OK`

- [ ] **Step 5: Verify TypeScript types compile cleanly**

```bash
cd packages/node && npx tsc --noEmit
```

Expected: No type errors

- [ ] **Step 6: Final git status check**

```bash
git status
```

Expected: Clean working tree

- [ ] **Step 7: Commit any final fixups if needed**

```bash
git add -A && git commit -m "chore: final verification pass"
```
