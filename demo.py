"""
广西大学文件管理系统 API 演示脚本
"""

import json
import os
import sys
from client import WjxtClient


def _load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


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
        print(f"    [{d['id']}] {d['tn_decoded']}")
    if len(depts) > 10:
        print(f"    ... 还有 {len(depts) - 10} 个")
    print()


def demo_file_list(client: WjxtClient):
    """演示：文件列表 & 翻页"""
    print("=" * 60)
    print("[3] 文件列表 (第1页)")
    print("=" * 60)

    html = client.get_file_list(page=1)
    files = client.parse_file_list(html)
    page_info = client.get_pagination_info(html)

    print(f"  分页信息: {page_info}")
    print(f"  本页文件数: {len(files)}")
    print(f"  前5条:")
    for f in files[:5]:
        unread = " [未读]" if f["is_unread"] else ""
        print(f"    [{f['index']}] {f['department']}: {f['title'][:60]} ({f['date']}){unread}")

    # 翻到第2页
    if page_info.get("total_pages", 1) > 1:
        print(f"\n  翻到第 2 页...")
        html2 = client.get_file_list(page=2)
        files2 = client.parse_file_list(html2)
        page_info2 = client.get_pagination_info(html2)
        print(f"  第2页: {page_info2['current_page']}/{page_info2['total_pages']} 页, {len(files2)} 条")
        if files2:
            print(f"  第2页第1条: {files2[0]['department']}: {files2[0]['title'][:60]}")
    print()


def demo_department_files(client: WjxtClient):
    """演示：部门文件"""
    print("=" * 60)
    print("[4] 部门文件")
    print("=" * 60)

    # 获取某个部门的文件 (例如: 学工部 id=16)
    dept_id = 16
    dept_name = "学工部（处）、武装部（就业中心）"
    html = client.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=1)
    files = client.parse_file_list(html)
    pinfo = client.get_pagination_info(html)

    print(f"  [{dept_id}] {dept_name}")
    print(f"  分页信息: {pinfo}")
    print(f"  文件数: {len(files)}")
    for f in files[:5]:
        print(f"    [{f['index']}] {f['title'][:60]} ({f['date']})")
    print()


def demo_file_detail(client: WjxtClient):
    """演示：文件详情 & 下载"""
    print("=" * 60)
    print("[5] 文件详情 & 下载")
    print("=" * 60)

    # 先取列表拿到第一个文件 ID
    html = client.get_file_list(page=1)
    files = client.parse_file_list(html)

    if not files:
        print("  没有可用文件")
        print()
        return

    first_file = files[0]
    file_id = first_file["id"]

    if file_id:
        detail = client.get_file_detail(file_id)
        print(f"  文件 ID: {file_id}")
        print(f"  标题: {detail['title']}")
        print(f"  下载 URL: {detail['download_url']}")

        if detail["download_url"]:
            # 下载文件
            filepath = client.download_file(file_id=file_id,
                                            save_dir=os.path.dirname(os.path.abspath(__file__)))
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

    html = client.get_phone_list()
    contacts = client.parse_phone_list(html)
    print(f"  联系人数量: {len(contacts)}")
    for c in contacts[:10]:
        print(f"    {c['name']}: {c['phone']} {c['extra']}")
    if len(contacts) > 10:
        print(f"    ... 还有 {len(contacts) - 10} 人")
    print()


def demo_business(client: WjxtClient):
    """演示：业务办理"""
    print("=" * 60)
    print("[7] 业务办理")
    print("=" * 60)

    html = client.get_todo_list()
    print(f"  待办列表: {len(html)} 字节")

    html2 = client.get_my_todo_lists()
    print(f"  我的待办: {len(html2)} 字节")

    html3 = client.get_my_update_lists()
    print(f"  我的更新: {len(html3)} 字节")

    html4 = client.get_business_add_page()
    print(f"  新增业务页: {len(html4)} 字节")
    print()


def demo_password(client: WjxtClient):
    """演示：密码修改页面"""
    print("=" * 60)
    print("[8] 修改密码页面")
    print("=" * 60)

    html = client.get_password_page()
    print(f"  页面大小: {len(html)} 字节")
    print(f"  包含密码修改表单: {'userPWD1' in html}")
    # 注意: 实际修改密码需要调用 client.change_password(old, new)
    # 此处仅演示获取页面
    print()


def demo_search(client: WjxtClient):
    """演示：搜索"""
    print("=" * 60)
    print("[9] 搜索")
    print("=" * 60)

    html = client.search_files(keyword="通知")
    is_maintenance = "维护" in html
    print(f"  搜索结果: {len(html)} 字节")
    print(f"  {'系统维护中，搜索功能暂不可用' if is_maintenance else '可用'}")
    print()


def demo_logout(client: WjxtClient):
    """演示：退出登录"""
    print("=" * 60)
    print("[10] 退出登录")
    print("=" * 60)
    client.logout()
    print("  已退出登录")
    print()


def main():
    # 禁用 SSL 警告
    import urllib3
    urllib3.disable_warnings()

    config = _load_config()
    client = WjxtClient(config.get("username", ""), config.get("password", ""))

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
        ("退出登录", demo_logout),
    ]

    for name, func in demos:
        try:
            func(client)
        except Exception as e:
            print(f"  [!] {name} 出错: {e}")
            print()

    print("=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
