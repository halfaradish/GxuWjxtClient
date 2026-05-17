"""
广西大学文件管理系统 — 文件下载爬虫

用法:
    python crawler.py                          # 下载全部文件到 ./downloads
    python crawler.py -o /path/to/dir          # 指定输出目录
    python crawler.py -d 16 -n 3               # 只下载学工部最近3页
    python crawler.py -d all -n 5              # 所有部门各取5页
    python crawler.py --unread-only            # 仅下载未读文件
    python crawler.py --after 2026-03-01       # 仅下载指定日期之后的文件
    python crawler.py --workers 5              # 5 线程并发下载
    python crawler.py --dry-run                # 预览，不实际下载
"""

import argparse
import os
import sys
import time
import json
import hashlib
import threading
from pathlib import Path
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import urllib3
urllib3.disable_warnings()

from client import WjxtClient

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """加载配置文件，优先读取 config.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

HISTORY_FILE = "download_history.json"   # 下载记录（避免重复下载）
RETRY_COUNT = 3                          # 单文件最大重试次数
RETRY_DELAY = 2                          # 重试间隔（秒）
PAGE_DELAY = 0.5                         # 翻页间隔（秒），避免服务器压力

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class CrawlStats:
    total_files: int = 0
    downloaded: int = 0
    skipped: int = 0      # 已下载过，跳过
    no_attachment: int = 0  # 无附件可下载
    failed: int = 0         # 下载失败（网络/服务器错误）
    lock: threading.Lock = field(default_factory=threading.Lock)

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


# ---------------------------------------------------------------------------
# 下载记录管理
# ---------------------------------------------------------------------------


def load_history(path: str) -> set:
    """加载已下载文件的哈希集合"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("downloaded", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_history(path: str, downloaded: set):
    """保存下载记录"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.now().isoformat(),
            "count": len(downloaded),
            "downloaded": sorted(downloaded),
        }, f, ensure_ascii=False, indent=2)


def file_hash(file_id: int) -> str:
    """生成文件唯一标识"""
    return hashlib.md5(f"wjxt_file_{file_id}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# 文件名清理
# ---------------------------------------------------------------------------


def safe_filename(name: str, max_len: int = 120) -> str:
    """去除文件名中的非法字符"""
    illegal = r'[<>:"/\\|?*\r\n\t]'
    clean = ""
    for ch in name:
        if ch in '<>:"/\\|?*':
            clean += "_"
        elif ch in '\r\n\t':
            continue
        else:
            clean += ch
    clean = clean.strip(". ")
    if not clean:
        clean = "unnamed"
    return clean[:max_len]


# ---------------------------------------------------------------------------
# 下载器
# ---------------------------------------------------------------------------


def _download_raw(client: WjxtClient, url: str, save_path: str,
                  stats: CrawlStats) -> bool:
    """下载单个 URL 的原始字节到指定路径"""
    for attempt in range(RETRY_COUNT):
        try:
            if url.startswith("/"):
                url = client.BASE_URL + url
            resp = client._get(url, headers={"Referer": f"{client.WJXT_UI}/showfile.aspx"})
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            if attempt < RETRY_COUNT - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"    [FAIL] {os.path.basename(save_path)} -> {e}")
                return False
    return False


def download_one(client: WjxtClient, file_info: dict, output_dir: str,
                 history: set, stats: CrawlStats, history_path: str,
                 dry_run: bool = False) -> Optional[str]:
    """下载单个文件及其所有附件，返回本地路径或 None"""
    file_id = file_info["id"]
    fhash = file_hash(file_id)

    if fhash in history:
        stats.inc_skipped()
        return None

    if not file_id:
        stats.inc_no_attachment()
        return None

    # 获取详情
    detail = None
    for attempt in range(RETRY_COUNT):
        try:
            detail = client.get_file_detail(file_id)
            if detail and detail.get("raw_html"):
                break
        except Exception:
            if attempt < RETRY_COUNT - 1:
                time.sleep(RETRY_DELAY)

    if not detail or not detail.get("raw_html"):
        stats.inc_no_attachment()
        return None

    attachments = detail.get("download_urls", [])

    # 构建目录路径
    dept = safe_filename(file_info.get("department") or "广西大学", max_len=40)
    date_str = file_info.get("date", "0000-00-00")
    title = safe_filename(file_info.get("title", "无标题"), max_len=80)

    dept_dir = os.path.join(output_dir, dept)
    file_dir_name = safe_filename(f"{date_str}_{title}", max_len=100)
    file_dir = os.path.join(dept_dir, file_dir_name)

    if dry_run:
        tag = f"{len(attachments)} 个附件" if attachments else "仅 HTML"
        print(f"  [DRY-RUN] {dept}/{file_dir_name}/ ({tag})")
        for att in attachments:
            print(f"    -> {att['filename']}")
        history.add(fhash)
        stats.inc_downloaded()
        save_history(history_path, history)
        return file_dir

    os.makedirs(file_dir, exist_ok=True)

    # 保存 HTML 页面本身（showfile.aspx 的内容即文件正文）
    html_filename = safe_filename(f"{date_str}_{title}.html", max_len=120)
    html_path = os.path.join(file_dir, html_filename)
    if not os.path.exists(html_path):
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(detail["raw_html"])

    # 下载所有附件
    saved_count = 0
    for att in attachments:
        att_filename = safe_filename(att["filename"])
        att_path = os.path.join(file_dir, att_filename)

        if os.path.exists(att_path):
            saved_count += 1
            continue

        if _download_raw(client, att["url"], att_path, stats):
            saved_count += 1
        else:
            print(f"\n    [FAIL] {att_filename}")

    history.add(fhash)
    stats.inc_downloaded()
    save_history(history_path, history)
    return file_dir


def _progress_bar(done: int, total: int, width: int = 20) -> str:
    """生成进度条字符串 [====>     ] 12/50  24%"""
    if total <= 0:
        return ""
    filled = int(width * done / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = done / total * 100
    return f"  [{bar}] {done}/{total}  {pct:.0f}%"


def download_batch(client: WjxtClient, files: list[dict], output_dir: str,
                   history: set, stats: CrawlStats, history_path: str,
                   workers: int = 1, dry_run: bool = False):
    """批量下载文件列表"""
    total = len(files)
    if total == 0:
        return

    if workers <= 1:
        for i, f in enumerate(files):
            download_one(client, f, output_dir, history, stats, history_path, dry_run)
            print(f"\r{_progress_bar(i + 1, total)}", end="", flush=True)
        print()  # 换行
    else:
        client_lock = threading.Lock()
        done_count = [0]  # mutable counter for thread-safe increments
        count_lock = threading.Lock()

        def _download_safe(finfo):
            result = None
            with client_lock:
                result = download_one(client, finfo, output_dir, history, stats, history_path, dry_run)
            with count_lock:
                done_count[0] += 1
                print(f"\r{_progress_bar(done_count[0], total)}", end="", flush=True)
            return result

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_download_safe, f) for f in files]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"\n  [ERR] {e}")
        print()  # 换行


# ---------------------------------------------------------------------------
# 主逻辑
# ---------------------------------------------------------------------------


def parse_date(s: str) -> Optional[date]:
    """解析日期字符串"""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {s}")


def filter_files(files: list[dict], after: Optional[date] = None,
                 unread_only: bool = False) -> list[dict]:
    """过滤文件列表"""
    result = []
    for f in files:
        if unread_only and not f["is_unread"]:
            continue
        if after and f["date"]:
            try:
                fd = datetime.strptime(f["date"], "%Y-%m-%d").date()
                if fd < after:
                    continue
            except ValueError:
                pass
        result.append(f)
    return result


def crawl_department(client: WjxtClient, dept_id: int, dept_name: str,
                     output_dir: str, history: set, stats: CrawlStats,
                     history_path: str, max_pages: Optional[int],
                     after: Optional[date], unread_only: bool,
                     workers: int, dry_run: bool):
    """爬取单个部门的文件"""
    # 获取第1页
    html = client.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=1)
    page_info = client.get_pagination_info(html)
    files = client.parse_file_list(html)

    total_pages = page_info.get("total_pages", 1)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    stats.total_files += len(files)

    filtered = filter_files(files, after=after, unread_only=unread_only)
    print(f"\n  [{dept_id}] {dept_name}")
    print(f"  第 1/{total_pages} 页, 本页 {len(files)} 条, 符合条件 {len(filtered)} 条")

    if filtered:
        download_batch(client, filtered, output_dir, history, stats, history_path, workers, dry_run)

    # 翻页
    for p in range(2, total_pages + 1):
        time.sleep(PAGE_DELAY)
        html = client.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=p)
        files = client.parse_file_list(html)
        stats.total_files += len(files)

        filtered = filter_files(files, after=after, unread_only=unread_only)
        pct = p / total_pages * 100
        print(f"\n  第 {p}/{total_pages} 页 [{pct:.0f}%], 本页 {len(files)} 条, 符合条件 {len(filtered)} 条")

        if filtered:
            download_batch(client, filtered, output_dir, history, stats, history_path, workers, dry_run)


def crawl_all_files(client: WjxtClient, output_dir: str, history: set,
                    stats: CrawlStats, history_path: str,
                    max_pages: Optional[int], after: Optional[date],
                    unread_only: bool, workers: int, dry_run: bool):
    """爬取全部文件（不分部门）"""
    html = client.get_file_list(page=1)
    page_info = client.get_pagination_info(html)
    files = client.parse_file_list(html)

    total_pages = page_info.get("total_pages", 1)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    stats.total_files += len(files)
    filtered = filter_files(files, after=after, unread_only=unread_only)

    print(f"\n[全部文件] 第 1/{total_pages} 页, 本页 {len(files)} 条, 符合条件 {len(filtered)} 条")
    if filtered:
        download_batch(client, filtered, output_dir, history, stats, history_path, workers, dry_run)

    for p in range(2, total_pages + 1):
        time.sleep(PAGE_DELAY)
        html = client.get_file_list(page=p)
        files = client.parse_file_list(html)
        stats.total_files += len(files)

        filtered = filter_files(files, after=after, unread_only=unread_only)
        pct = p / total_pages * 100
        print(f"\n第 {p}/{total_pages} 页 [{pct:.0f}%], 本页 {len(files)} 条, 符合条件 {len(filtered)} 条")

        if filtered:
            download_batch(client, filtered, output_dir, history, stats, history_path, workers, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="广西大学文件管理系统 — 文件下载爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-o", "--output", default="./downloads",
                        help="下载目录 (默认: ./downloads)")
    parser.add_argument("-d", "--dept", default=None,
                        help="部门 ID 或 'all' (默认: 全部文件，不分部门)")
    parser.add_argument("-n", "--max-pages", type=int, default=None,
                        help="每个部门/列表最多爬取页数 (默认: 全部)")
    parser.add_argument("--after", default=None,
                        help="只下载此日期之后的文件 (格式: YYYY-MM-DD)")
    parser.add_argument("--unread-only", action="store_true",
                        help="仅下载未读文件")
    parser.add_argument("--workers", type=int, default=1,
                        help="并发下载线程数 (默认: 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览模式，不实际下载文件")
    cfg = _load_config()
    parser.add_argument("-u", "--username", default=None,
                        help="用户名 (默认: 读取 config.json)")
    parser.add_argument("-p", "--password", default=None,
                        help="密码   (默认: 读取 config.json)")

    args = parser.parse_args()

    # 命令行未提供则从配置文件读取
    if args.username is None:
        args.username = cfg.get("username", "")
    if args.password is None:
        args.password = cfg.get("password", "")

    # 解析日期过滤
    after_date = None
    if args.after:
        try:
            after_date = parse_date(args.after)
            print(f"日期过滤: >= {after_date}")
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)

    # 创建输出目录
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    # 加载下载记录
    history_path = os.path.join(output_dir, HISTORY_FILE)
    history = load_history(history_path)
    print(f"已下载记录: {len(history)} 条")

    # 初始化客户端
    client = WjxtClient(args.username, args.password)
    print("登录中...")
    if not client.login():
        print("登录失败!")
        sys.exit(1)
    print("登录成功\n")

    stats = CrawlStats()
    t0 = time.time()

    try:
        if args.dept is None:
            # 默认：全部文件，不分部门
            crawl_all_files(
                client, output_dir, history, stats, history_path,
                max_pages=args.max_pages, after=after_date,
                unread_only=args.unread_only, workers=args.workers,
                dry_run=args.dry_run,
            )
        elif args.dept.lower() == "all":
            # 遍历所有部门
            depts = client.get_departments()
            print(f"共 {len(depts)} 个部门\n")
            for i, d in enumerate(depts):
                print(f"{'=' * 50}")
                print(f"部门 [{i + 1}/{len(depts)}]")           
                try:
                    crawl_department(
                        client, d["id"], d["tn_decoded"], output_dir,
                        history, stats, history_path,
                        max_pages=args.max_pages, after=after_date,
                        unread_only=args.unread_only, workers=args.workers,
                        dry_run=args.dry_run,
                    )
                except Exception as e:
                    print(f"  [跳过] 部门 [{d['id']}] {d['tn_decoded']} 出错: {e}")
        else:
            # 指定部门 ID
            dept_id = int(args.dept)
            depts = client.get_departments()
            dept_name = ""
            for d in depts:
                if d["id"] == dept_id:
                    dept_name = d["tn_decoded"]
                    break
            if not dept_name:
                dept_name = f"部门{dept_id}"

            crawl_department(
                client, dept_id, dept_name, output_dir,
                history, stats, history_path,
                max_pages=args.max_pages, after=after_date,
                unread_only=args.unread_only, workers=args.workers,
                dry_run=args.dry_run,
            )

    except KeyboardInterrupt:
        print("\n\n用户中断。")
    finally:
        save_history(history_path, history)
        client.logout()

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"完成！耗时 {elapsed:.0f} 秒")
    print(f"  扫描文件:   {stats.total_files}")
    print(f"  新下载:     {stats.downloaded}")
    print(f"  已跳过:     {stats.skipped}")
    print(f"  无附件:     {stats.no_attachment}")
    print(f"  下载失败:   {stats.failed}")
    print(f"  输出目录:   {output_dir}")


if __name__ == "__main__":
    main()
