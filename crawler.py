"""
向后兼容 shim — 从 gxu_wjxt 重新导出
新代码请直接使用: from gxu_wjxt import FileCrawler
"""

from gxu_wjxt.crawler import FileCrawler
from gxu_wjxt.cli import main

__all__ = ["FileCrawler", "main"]

if __name__ == "__main__":
    main()
