"""gxu-wjxt — 广西大学文件管理系统 Python SDK"""

from .client import WjxtClient
from .async_client import AsyncWjxtClient
from .crawler import FileCrawler
from .config import WjxtConfig
from .exceptions import (
    WjxtError,
    AuthError,
    NetworkError,
    ParseError,
    SessionExpiredError,
    DownloadError,
)
from .types import (
    FileInfo,
    FileDetail,
    Attachment,
    DepartmentInfo,
    PhoneContact,
    PaginationInfo,
    SearchParams,
    SearchResult,
    CrawlStats,
)

__all__ = [
    # 客户端
    "WjxtClient",
    "AsyncWjxtClient",
    # 爬虫
    "FileCrawler",
    # 配置
    "WjxtConfig",
    # 异常
    "WjxtError",
    "AuthError",
    "NetworkError",
    "ParseError",
    "SessionExpiredError",
    "DownloadError",
    # 数据类
    "FileInfo",
    "FileDetail",
    "Attachment",
    "DepartmentInfo",
    "PhoneContact",
    "PaginationInfo",
    "SearchParams",
    "SearchResult",
    "CrawlStats",
]
