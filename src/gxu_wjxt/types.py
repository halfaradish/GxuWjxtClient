from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class PaginationInfo:
    current_page: int = 1
    total_pages: int = 1
    per_page: int = 50
    total_items: int = 0


@dataclass
class FileInfo:
    id: Optional[int]
    index: str = ""
    title: str = ""
    department: str = ""
    date: str = ""  # YYYY-MM-DD
    is_unread: bool = False
    detail_url: str = ""


@dataclass
class Attachment:
    url: str
    filename: str


@dataclass
class FileDetail:
    file_id: int
    title: str = ""
    detail_url: str = ""
    raw_html: str = ""
    download_urls: list[Attachment] = field(default_factory=list)

    @property
    def download_url(self) -> str:
        """向后兼容：返回第一个附件 URL"""
        return self.download_urls[0].url if self.download_urls else ""


@dataclass
class DepartmentInfo:
    id: int
    type: int = 0
    tn_encoded: str = ""
    tn_decoded: str = ""
    url: str = ""


@dataclass
class PhoneContact:
    name: str = ""
    phone: str = ""
    extra: str = ""


@dataclass
class CrawlStats:
    total_files: int = 0
    downloaded: int = 0
    skipped: int = 0
    no_attachment: int = 0
    failed: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc_downloaded(self):
        with self.lock:
            self.downloaded += 1

    def inc_skipped(self):
        with self.lock:
            self.skipped += 1

    def inc_no_attachment(self):
        with self.lock:
            self.no_attachment += 1

    def inc_failed(self):
        with self.lock:
            self.failed += 1
