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
  pageTitle: string;
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
