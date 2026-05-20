"""文件下载爬虫 — 支持同步和异步客户端"""

from __future__ import annotations

import asyncio
import json
import os
import time
import threading
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Union

from .client import WjxtClient
from .async_client import AsyncWjxtClient
from .config import WjxtConfig
from .types import FileInfo, FileDetail, CrawlStats
from .exceptions import DownloadError
from . import _base

ClientType = Union[WjxtClient, AsyncWjxtClient]


class FileCrawler:
    """文件下载爬虫

    用法:
        client = WjxtClient(username="学号", password="密码")
        client.login()
        crawler = FileCrawler(client, download_dir="./downloads")
        crawler.crawl_all(max_pages=5, unread_only=True)
    """

    def __init__(self, client: ClientType, download_dir: str = "./downloads",
                 workers: int = 1, page_delay: float = 0.5):
        self._client = client
        self.download_dir = os.path.abspath(download_dir)
        self.workers = workers
        self.page_delay = page_delay

        os.makedirs(self.download_dir, exist_ok=True)

        self._history_path = os.path.join(self.download_dir, "download_history.json")
        self._history: set[str] = self._load_history()

    @property
    def client(self):
        return self._client

    @property
    def history(self) -> set[str]:
        return self._history

    # ------------------------------------------------------------------
    # 下载记录
    # ------------------------------------------------------------------

    def _load_history(self) -> set[str]:
        try:
            with open(self._history_path, encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("downloaded", []))
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    def _save_history(self):
        with open(self._history_path, "w", encoding="utf-8") as f:
            json.dump({
                "updated": datetime.now().isoformat(),
                "count": len(self._history),
                "downloaded": sorted(self._history),
            }, f, ensure_ascii=False, indent=2)

    def clear_history(self):
        """清除下载记录"""
        self._history.clear()
        if os.path.exists(self._history_path):
            os.remove(self._history_path)

    # ------------------------------------------------------------------
    # 过滤
    # ------------------------------------------------------------------

    @staticmethod
    def filter_files(files: list[FileInfo], after: date = None,
                     unread_only: bool = False) -> list[FileInfo]:
        result = []
        for f in files:
            if unread_only and not f.is_unread:
                continue
            if after and f.date:
                try:
                    fd = datetime.strptime(f.date, "%Y-%m-%d").date()
                    if fd < after:
                        continue
                except ValueError:
                    pass
            result.append(f)
        return result

    # ------------------------------------------------------------------
    # 单文件下载
    # ------------------------------------------------------------------

    def download_one(self, file_info: FileInfo, dry_run: bool = False) -> Optional[str]:
        """下载单个文件及其所有附件，返回本地目录路径"""
        file_id = file_info.id
        fhash = _base.file_hash(file_id)

        if fhash in self._history:
            return None

        if not file_id:
            return None

        # 获取详情 (带重试)
        detail = None
        for attempt in range(3):
            try:
                detail = self._client.get_file_detail(file_id)
                if detail and detail.raw_html:
                    break
            except Exception:
                if attempt < 2:
                    time.sleep(2)

        if not detail or not detail.raw_html:
            return None

        attachments = detail.download_urls

        # 构建目录
        dept = _base.safe_filename(file_info.department or "广西大学", max_len=40)
        date_str = file_info.date or "0000-00-00"
        title = _base.safe_filename(file_info.title or "无标题", max_len=80)

        dept_dir = os.path.join(self.download_dir, dept)
        file_dir_name = _base.safe_filename(f"{date_str}_{title}", max_len=100)
        file_dir = os.path.join(dept_dir, file_dir_name)

        if dry_run:
            tag = f"{len(attachments)} 个附件" if attachments else "仅 HTML"
            print(f"  [DRY-RUN] {dept}/{file_dir_name}/ ({tag})")
            for att in attachments:
                print(f"    -> {att.filename}")
            self._history.add(fhash)
            self._save_history()
            return file_dir

        os.makedirs(file_dir, exist_ok=True)

        # 保存 HTML 正文
        html_filename = _base.safe_filename(f"{date_str}_{title}.html", max_len=120)
        html_path = os.path.join(file_dir, html_filename)
        if not os.path.exists(html_path):
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(detail.raw_html)

        # 下载附件
        for att in attachments:
            att_filename = _base.safe_filename(att.filename)
            att_path = os.path.join(file_dir, att_filename)

            if os.path.exists(att_path):
                continue

            for attempt in range(3):
                try:
                    url = att.url
                    if url.startswith("/"):
                        url = self._client.base_url + url
                    resp = self._client._get(
                        url,
                        headers={"Referer": f"{self._client.wjxt_ui}/showfile.aspx"},
                    )
                    with open(att_path, "wb") as f:
                        f.write(resp.content)
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(2)

        self._history.add(fhash)
        self._save_history()
        return file_dir

    # ------------------------------------------------------------------
    # 批量下载
    # ------------------------------------------------------------------

    def download_batch(self, files: list[FileInfo], dry_run: bool = False) -> CrawlStats:
        """批量下载"""
        stats = CrawlStats()
        total = len(files)
        if total == 0:
            return stats

        stats.total_files = total

        if self.workers <= 1:
            for i, f_item in enumerate(files):
                fhash = _base.file_hash(f_item.id) if f_item.id else None

                if fhash and fhash in self._history:
                    stats.inc_skipped()
                elif not f_item.id:
                    stats.inc_no_attachment()
                else:
                    result = self.download_one(f_item, dry_run=dry_run)
                    if result:
                        stats.inc_downloaded()
                    else:
                        stats.inc_failed()

                bar = self._progress_bar(i + 1, total)
                print(f"\r{bar}", end="", flush=True)
            print()
        else:
            # 多线程下载
            client_lock = threading.Lock()
            done_count = [0]
            count_lock = threading.Lock()

            def _download_safe(finfo):
                fhash = _base.file_hash(finfo.id) if finfo.id else None

                if fhash and fhash in self._history:
                    stats.inc_skipped()
                elif not finfo.id:
                    stats.inc_no_attachment()
                else:
                    with client_lock:
                        try:
                            result = self.download_one(finfo, dry_run=dry_run)
                            if result:
                                stats.inc_downloaded()
                            else:
                                stats.inc_failed()
                        except Exception:
                            stats.inc_failed()

                with count_lock:
                    done_count[0] += 1
                    bar = self._progress_bar(done_count[0], total)
                    print(f"\r{bar}", end="", flush=True)

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = [executor.submit(_download_safe, f) for f in files]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass
            print()

        return stats

    # ------------------------------------------------------------------
    # 爬取策略
    # ------------------------------------------------------------------

    def crawl_all(self, max_pages: int = None, after: date = None,
                  unread_only: bool = False, dry_run: bool = False,
                  max_empty_pages: int = 3) -> CrawlStats:
        """爬取全部文件（不分部门）

        max_empty_pages: 连续多少页无匹配记录时自动停止，默认 3。
                         设为 0 禁用提前停止。
        """
        all_stats = CrawlStats()

        html = self._client.get_file_list(page=1)
        page_info = _base.parse_pagination_info(html)
        files = _base.parse_file_list(html, self._client.wjxt_ui)

        total_pages = page_info.total_pages
        if max_pages:
            total_pages = min(total_pages, max_pages)

        filtered = self.filter_files(files, after=after, unread_only=unread_only)
        print(f"\n[全部文件] 第 1/{total_pages} 页, 本页 {len(files)} 条, 符合条件 {len(filtered)} 条")

        empty_streak = 0 if filtered else 1

        if filtered:
            stats = self.download_batch(filtered, dry_run=dry_run)
            all_stats.total_files += len(files)
            all_stats.downloaded += stats.downloaded
            all_stats.skipped += stats.skipped
            all_stats.no_attachment += stats.no_attachment
            all_stats.failed += stats.failed

        for p in range(2, total_pages + 1):
            time.sleep(self.page_delay)
            html = self._client.get_file_list(page=p)
            files = _base.parse_file_list(html, self._client.wjxt_ui)

            filtered = self.filter_files(files, after=after, unread_only=unread_only)
            pct = p / total_pages * 100
            print(f"\n第 {p}/{total_pages} 页 [{pct:.0f}%], 本页 {len(files)} 条, 符合条件 {len(filtered)} 条")

            if not filtered:
                if max_empty_pages > 0:
                    empty_streak += 1
                    if empty_streak >= max_empty_pages:
                        print(f"  连续 {empty_streak} 页无匹配记录，停止翻页。")
                        break
                continue

            empty_streak = 0
            stats = self.download_batch(filtered, dry_run=dry_run)
            all_stats.total_files += len(files)
            all_stats.downloaded += stats.downloaded
            all_stats.skipped += stats.skipped
            all_stats.no_attachment += stats.no_attachment
            all_stats.failed += stats.failed

        return all_stats

    def crawl_department(self, dept_id: int, dept_name: str = "",
                         max_pages: int = None, after: date = None,
                         unread_only: bool = False,
                         dry_run: bool = False,
                         max_empty_pages: int = 3) -> CrawlStats:
        """爬取指定部门文件

        max_empty_pages: 连续多少页无匹配记录时自动停止，默认 3。
                         设为 0 禁用提前停止。
        """
        all_stats = CrawlStats()

        html = self._client.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=1)
        page_info = _base.parse_pagination_info(html)
        files = _base.parse_file_list(html, self._client.wjxt_ui)

        total_pages = page_info.total_pages
        if max_pages:
            total_pages = min(total_pages, max_pages)

        filtered = self.filter_files(files, after=after, unread_only=unread_only)
        print(f"\n  [{dept_id}] {dept_name}")
        print(f"  第 1/{total_pages} 页, 本页 {len(files)} 条, 符合条件 {len(filtered)} 条")

        empty_streak = 0 if filtered else 1

        if filtered:
            stats = self.download_batch(filtered, dry_run=dry_run)
            all_stats.total_files += len(files)
            all_stats.downloaded += stats.downloaded
            all_stats.skipped += stats.skipped
            all_stats.no_attachment += stats.no_attachment
            all_stats.failed += stats.failed

        for p in range(2, total_pages + 1):
            time.sleep(self.page_delay)
            html = self._client.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=p)
            files = _base.parse_file_list(html, self._client.wjxt_ui)

            filtered = self.filter_files(files, after=after, unread_only=unread_only)
            pct = p / total_pages * 100
            print(f"\n  第 {p}/{total_pages} 页 [{pct:.0f}%], 本页 {len(files)} 条, 符合条件 {len(filtered)} 条")

            if not filtered:
                if max_empty_pages > 0:
                    empty_streak += 1
                    if empty_streak >= max_empty_pages:
                        print(f"  连续 {empty_streak} 页无匹配记录，停止翻页。")
                        break
                continue

            empty_streak = 0
            stats = self.download_batch(filtered, dry_run=dry_run)
            all_stats.total_files += len(files)
            all_stats.downloaded += stats.downloaded
            all_stats.skipped += stats.skipped
            all_stats.no_attachment += stats.no_attachment
            all_stats.failed += stats.failed

        return all_stats

    def crawl_all_departments(self, max_pages: int = None, after: date = None,
                              unread_only: bool = False,
                              dry_run: bool = False,
                              max_empty_pages: int = 3) -> CrawlStats:
        """爬取所有部门的文件"""
        depts = self._client.get_departments()
        print(f"共 {len(depts)} 个部门\n")

        all_stats = CrawlStats()
        for i, d in enumerate(depts):
            print(f"{'=' * 50}")
            print(f"部门 [{i + 1}/{len(depts)}]")
            try:
                stats = self.crawl_department(
                    d.id, d.tn_decoded,
                    max_pages=max_pages, after=after,
                    unread_only=unread_only, dry_run=dry_run,
                    max_empty_pages=max_empty_pages,
                )
                all_stats.total_files += stats.total_files
                all_stats.downloaded += stats.downloaded
                all_stats.skipped += stats.skipped
                all_stats.no_attachment += stats.no_attachment
                all_stats.failed += stats.failed
            except Exception as e:
                print(f"  [跳过] 部门 [{d.id}] {d.tn_decoded} 出错: {e}")

        return all_stats

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _progress_bar(done: int, total: int, width: int = 20) -> str:
        if total <= 0:
            return ""
        filled = int(width * done / total)
        bar = "█" * filled + "░" * (width - filled)
        pct = done / total * 100
        return f"  [{bar}] {done}/{total}  {pct:.0f}%"
