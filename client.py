"""
向后兼容 shim — 从 gxu_wjxt 重新导出
新代码请直接使用: from gxu_wjxt import WjxtClient
"""

from gxu_wjxt.client import WjxtClient
from gxu_wjxt.config import WjxtConfig
from gxu_wjxt.types import FileInfo, FileDetail, DepartmentInfo, PhoneContact, PaginationInfo

__all__ = [
    "WjxtClient",
    "WjxtConfig",
    "FileInfo",
    "FileDetail",
    "DepartmentInfo",
    "PhoneContact",
    "PaginationInfo",
]
