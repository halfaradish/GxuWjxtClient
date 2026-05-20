class WjxtError(Exception):
    """SDK 基础异常"""
    pass


class AuthError(WjxtError):
    """认证失败"""
    pass


class NetworkError(WjxtError):
    """网络请求失败"""
    pass


class ParseError(WjxtError):
    """HTML 解析失败"""
    pass


class SessionExpiredError(WjxtError):
    """会话过期，需重新登录"""
    pass


class DownloadError(WjxtError):
    """文件下载失败"""
    pass
