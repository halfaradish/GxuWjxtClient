from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class WjxtConfig:
    """SDK 全局配置

    优先级: 构造参数 > 环境变量 > 配置文件 > 默认值
    """

    username: str = ""
    password: str = ""

    base_url: str = "https://wjxt.gxu.edu.cn"
    myteip: str = "172.28.222.133--2"

    # HTTP 配置
    timeout: float = 30.0
    max_redirects: int = 5
    verify_ssl: bool = False

    # 重试配置
    retry_count: int = 3
    retry_delay: float = 2.0

    # 爬虫配置
    download_dir: str = "./downloads"
    page_delay: float = 0.5
    history_file: str = "download_history.json"
    max_workers: int = 1

    # User-Agent
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    @classmethod
    def from_env(cls) -> WjxtConfig:
        """从环境变量加载"""
        return cls(
            username=os.environ.get("WJXT_USERNAME", ""),
            password=os.environ.get("WJXT_PASSWORD", ""),
            base_url=os.environ.get("WJXT_BASE_URL", cls.base_url),
            myteip=os.environ.get("WJXT_MYTEIP", cls.myteip),
            download_dir=os.environ.get("WJXT_DOWNLOAD_DIR", cls.download_dir),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> WjxtConfig:
        """从 JSON 配置文件加载"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            username=data.get("username", ""),
            password=data.get("password", ""),
            base_url=data.get("base_url", cls.base_url),
            myteip=data.get("myteip", cls.myteip),
            download_dir=data.get("download_dir", cls.download_dir),
        )

    def merge_with(self, **kwargs) -> WjxtConfig:
        """用给定值覆盖配置字段"""
        current = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        current.update({k: v for k, v in kwargs.items() if v is not None})
        return WjxtConfig(**current)
