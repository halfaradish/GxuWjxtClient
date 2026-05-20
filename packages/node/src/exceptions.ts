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
