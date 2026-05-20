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
        continue;
      } catch { /* need to download */ }

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
      // 并发控制：信号量模式 — 限制同时进行的 fetch 请求数
      let done = 0;

      const downloadWithSemaphore = async (f: FileInfo): Promise<void> => {
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

        done++;
        const bar = FileCrawler._progressBar(done, files.length);
        process.stdout.write(`\r${bar}`);
      };

      // 将文件分批处理，以 concurrency 为限
      for (let i = 0; i < files.length; i += this.concurrency) {
        const batch = files.slice(i, i + this.concurrency);
        await Promise.all(batch.map(f => downloadWithSemaphore(f)));
      }

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
