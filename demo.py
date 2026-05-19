"""
广西大学文件管理系统 API 演示脚本
"""

import os
from gxu_wjxt import WjxtClient, WjxtConfig


def demo_basic(client: WjxtClient):
    """演示：基本连接 & 登录"""
    print("=" * 60)
    print("[1] 登录系统")
    print("=" * 60)
    success = client.login()
    print(f"  登录结果: {'成功' if success else '失败'}")
    print()


def demo_main_pages(client: WjxtClient):
    """演示：获取主页、导航、部门列表"""
    print("=" * 60)
    print("[2] 获取主页 & 导航")
    print("=" * 60)

    main_html = client.get_main_page()
    print(f"  主页面: {len(main_html)} 字节")

    sidebar_html = client.get_sidebar()
    print(f"  侧边栏: {len(sidebar_html)} 字节")

    dept_html = client.get_department_list()
    print(f"  部门列表页: {len(dept_html)} 字节")

    depts = client.get_departments()
    print(f"  解析到 {len(depts)} 个部门:")
    for d in depts[:10]:
        print(f"    [{d.id}] {d.tn_decoded}")
    if len(depts) > 10:
        print(f"    ... 还有 {len(depts) - 10} 个")
    print()


def demo_file_list(client: WjxtClient):
    """演示：文件列表 & 翻页"""
    print("=" * 60)
    print("[3] 文件列表 (第1页)")
    print("=" * 60)

    files, page_info = client.get_file_list_structured(page=1)

    print(f"  分页信息: 第{page_info.current_page}页/总{page_info.total_pages}页, "
          f"每页{page_info.per_page}条/共{page_info.total_items}条")
    print(f"  本页文件数: {len(files)}")
    print(f"  前5条:")
    for f in files[:5]:
        unread = " [未读]" if f.is_unread else ""
        print(f"    [{f.index}] {f.department}: {f.title[:60]} ({f.date}){unread}")

    # 翻到第2页
    if page_info.total_pages > 1:
        print(f"\n  翻到第 2 页...")
        html2 = client.get_file_list(page=2)
        from gxu_wjxt._base import parse_file_list, parse_pagination_info
        files2 = parse_file_list(html2, client.wjxt_ui)
        page_info2 = parse_pagination_info(html2)
        print(f"  第2页: {page_info2.current_page}/{page_info2.total_pages} 页, {len(files2)} 条")
        if files2:
            print(f"  第2页第1条: {files2[0].department}: {files2[0].title[:60]}")
    print()


def demo_department_files(client: WjxtClient):
    """演示：部门文件"""
    print("=" * 60)
    print("[4] 部门文件")
    print("=" * 60)

    dept_id = 16
    dept_name = "学工部（处）、武装部（就业中心）"
    html = client.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=1)
    from gxu_wjxt._base import parse_file_list, parse_pagination_info
    files = parse_file_list(html, client.wjxt_ui)
    pinfo = parse_pagination_info(html)

    print(f"  [{dept_id}] {dept_name}")
    print(f"  分页信息: 第{pinfo.current_page}页/总{pinfo.total_pages}页")
    print(f"  文件数: {len(files)}")
    for f in files[:5]:
        print(f"    [{f.index}] {f.title[:60]} ({f.date})")
    print()


def demo_file_detail(client: WjxtClient):
    """演示：文件详情 & 下载"""
    print("=" * 60)
    print("[5] 文件详情 & 下载")
    print("=" * 60)

    html = client.get_file_list(page=1)
    from gxu_wjxt._base import parse_file_list
    files = parse_file_list(html, client.wjxt_ui)

    if not files:
        print("  没有可用文件")
        print()
        return

    first_file = files[0]
    file_id = first_file.id

    if file_id:
        detail = client.get_file_detail(file_id)
        print(f"  文件 ID: {file_id}")
        print(f"  标题: {detail.title}")
        print(f"  下载 URL: {detail.download_url}")
        print(f"  附件数: {len(detail.download_urls)}")

        if detail.download_url:
            filepath = client.download_file(
                file_id=file_id,
                save_dir=os.path.dirname(os.path.abspath(__file__)),
            )
            if filepath:
                size = os.path.getsize(filepath)
                print(f"  已下载到: {filepath} ({size} 字节)")
            else:
                print(f"  下载失败")
    print()


def demo_phone_list(client: WjxtClient):
    """演示：电话簿"""
    print("=" * 60)
    print("[6] 电话簿")
    print("=" * 60)

    contacts = client.parse_phone_list()
    print(f"  联系人数量: {len(contacts)}")
    for c in contacts[:10]:
        print(f"    {c.name}: {c.phone} {c.extra}")
    if len(contacts) > 10:
        print(f"    ... 还有 {len(contacts) - 10} 人")
    print()


def demo_business(client: WjxtClient):
    """演示：业务办理"""
    print("=" * 60)
    print("[7] 业务办理")
    print("=" * 60)

    for label, page in [
        ("待办列表", client.get_todo_list()),
        ("我的待办", client.get_my_todo_lists()),
        ("已批申请", client.get_todo_processing()),
        ("全部申请", client.get_my_update_lists()),
        ("新增业务", client.get_business_add_page()),
    ]:
        records_info = f", {len(page.records)} 条记录" if page.records else ""
        html_len = len(page.raw_html)
        nav = " > ".join(page.nav_links.keys()) if page.nav_links else "无导航"
        search = " [搜索框]" if page.has_search else ""
        print(f"  {label}: {html_len} 字节 | 标签: {nav}{search}{records_info}")
    print()


def demo_password(client: WjxtClient):
    """演示：密码修改页面"""
    print("=" * 60)
    print("[8] 修改密码页面")
    print("=" * 60)

    html = client.get_password_page()
    print(f"  页面大小: {len(html)} 字节")
    print(f"  包含密码修改表单: {'userPWD1' in html}")
    print()


def demo_search(client: WjxtClient):
    """演示：搜索"""
    print("=" * 60)
    print("[9] 搜索")
    print("=" * 60)

    result = client.search(keyword="通知", file_year="2026")
    print(f"  搜索 '通知' (2026年): 共 {result.total_count} 条, {result.total_pages} 页")
    for f in result.files[:5]:
        print(f"    [{f.index}] {f.department}: {f.title[:60]} ({f.date})")
    if result.total_count > 5:
        print(f"    ... 还有 {result.total_count - 5} 条")
    print()


def demo_generator(client: WjxtClient):
    """演示：惰性生成器遍历文件"""
    print("=" * 60)
    print("[10] 文件生成器 (前10条)")
    print("=" * 60)

    count = 0
    for f in client.iter_files(max_pages=1):
        unread = " [未读]" if f.is_unread else ""
        print(f"    [{f.index}] {f.department}: {f.title[:60]} ({f.date}){unread}")
        count += 1
        if count >= 10:
            break
    print()


def demo_logout(client: WjxtClient):
    """演示：退出登录"""
    print("=" * 60)
    print("[11] 退出登录")
    print("=" * 60)
    client.logout()
    print("  已退出登录")
    print()


def main():
    # 加载配置
    config = WjxtConfig.from_env()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_path):
        config = WjxtConfig.from_file(config_path)

    client = WjxtClient(username=config.username, password=config.password,
                        base_url=config.base_url, myteip=config.myteip)

    demos = [
        ("登录", demo_basic),
        ("主页 & 导航", demo_main_pages),
        ("文件列表 & 翻页", demo_file_list),
        ("部门文件", demo_department_files),
        ("文件详情 & 下载", demo_file_detail),
        ("电话簿", demo_phone_list),
        ("业务办理", demo_business),
        ("修改密码页面", demo_password),
        ("搜索", demo_search),
        ("文件生成器", demo_generator),
        ("退出登录", demo_logout),
    ]

    for name, func in demos:
        try:
            func(client)
        except Exception as e:
            print(f"  [!] {name} 出错: {e}")
            print()

    client.close()
    print("=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
