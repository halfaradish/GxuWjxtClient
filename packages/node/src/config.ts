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
