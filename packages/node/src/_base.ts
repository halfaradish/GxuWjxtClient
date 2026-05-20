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
    pageTitle: '',
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
