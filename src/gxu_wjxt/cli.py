"""CLI 入口 — python -m gxu_wjxt.cli 或 gxu-wjxt"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime

from .client import WjxtClient
from .crawler import FileCrawler
from .config import WjxtConfig


def parse_date(s: str) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {s}")


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
    parser.add_argument("-u", "--username", default=None, help="用户名")
    parser.add_argument("-p", "--password", default=None, help="密码")

    args = parser.parse_args()

    # 加载配置（环境变量优先）
    config = WjxtConfig.from_env()
    if args.username:
        config.username = args.username
    if args.password:
        config.password = args.password

    if not config.username or not config.password:
        # 尝试加载配置文件
        for cfg_path in ("./config.json", os.path.expanduser("~/.gxu_wjxt.json")):
            if os.path.exists(cfg_path):
                config = WjxtConfig.from_file(cfg_path)
                break
        else:
            print("错误: 未提供用户名/密码。请通过 -u/-p 参数、环境变量或 config.json 提供。")
            sys.exit(1)

    # 解析日期过滤
    after_date = None
    if args.after:
        try:
            after_date = parse_date(args.after)
            print(f"日期过滤: >= {after_date}")
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    client = WjxtClient(username=config.username, password=config.password,
                        base_url=config.base_url, myteip=config.myteip,
                        download_dir=output_dir)
    print("登录中...")
    if not client.login():
        print("登录失败!")
        sys.exit(1)
    print("登录成功\n")

    crawler = FileCrawler(client, download_dir=output_dir, workers=args.workers)
    t0 = time.time()

    try:
        if args.dept is None:
            stats = crawler.crawl_all(
                max_pages=args.max_pages, after=after_date,
                unread_only=args.unread_only, dry_run=args.dry_run,
            )
        elif args.dept.lower() == "all":
            stats = crawler.crawl_all_departments(
                max_pages=args.max_pages, after=after_date,
                unread_only=args.unread_only, dry_run=args.dry_run,
            )
        else:
            dept_id = int(args.dept)
            depts = client.get_departments()
            dept_name = ""
            for d in depts:
                if d.id == dept_id:
                    dept_name = d.tn_decoded
                    break
            if not dept_name:
                dept_name = f"部门{dept_id}"

            stats = crawler.crawl_department(
                dept_id, dept_name,
                max_pages=args.max_pages, after=after_date,
                unread_only=args.unread_only, dry_run=args.dry_run,
            )

    except KeyboardInterrupt:
        print("\n\n用户中断。")
    finally:
        crawler._save_history()
        client.logout()
        client.close()

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
