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
      if (name === 'path' || name === 'expires' || name === 'HttpOnly' || name === 'Secure') continue;
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
    await this._get(
      `${this.wjxtUi}/Exiting.aspx`,
      { headers: { Referer: `${this.wjxtUi}/default.aspx` } },
    );
    this._loggedIn = false;
    return true;
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

    // 用原始 fetch 下载二进制（不走 _get 的文本解码流程）
    const resp = await fetch(downloadUrl, {
      headers: {
        Cookie: this._cookieHeader(),
        'User-Agent': this._config.userAgent,
        Referer: `${this.wjxtUi}/showfile.aspx`,
      },
      signal: AbortSignal.timeout(this._config.timeout),
    });
    const buf = Buffer.from(await resp.arrayBuffer());

    const saveDir = opts.saveDir ?? '.';
    const urlPath = new URL(downloadUrl).pathname;
    const filename = path.basename(urlPath.split('?')[0]!);
    const filepath = path.join(saveDir, filename);

    await fs.mkdir(saveDir, { recursive: true });
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

    const doRequest = async (): Promise<string> => {
      const headers = new Headers({
        'Content-Type': 'application/x-www-form-urlencoded',
        Referer: `${this.wjxtUi}/WebUI.aspx?id=2`,
      });
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
    const p: SearchParams = params ?? { keyword: '', searchType: 'title', fileType: '全部文件', fileYear: '0', matchMode: 'Fuzzy' };
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
