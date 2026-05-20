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
