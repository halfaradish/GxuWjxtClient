"""
广西大学文件管理系统 (wjxt.gxu.edu.cn) Python 客户端
"""

import re
import os
import urllib3
import requests
from urllib.parse import urljoin, quote, unquote
from bs4 import BeautifulSoup

urllib3.disable_warnings()


class WjxtClient:
    BASE_URL = "https://wjxt.gxu.edu.cn"
    WJXT_UI = f"{BASE_URL}/Wjxt_UI"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        self._logged_in = False

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs) -> requests.Response:
        resp = self.session.get(url, timeout=30, **kwargs)
        resp.encoding = resp.apparent_encoding or "gb2312"
        return resp

    def _post(self, url: str, data: dict = None, **kwargs) -> requests.Response:
        resp = self.session.post(url, data=data, timeout=30, **kwargs)
        resp.encoding = resp.apparent_encoding or "gb2312"
        return resp

    def _extract_viewstate(self, html: str) -> dict:
        """提取 ASP.NET 隐藏表单字段"""
        fields = {}
        for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR",
                     "__SCROLLPOSITIONX", "__SCROLLPOSITIONY",
                     "__EVENTTARGET", "__EVENTARGUMENT"):
            m = re.search(rf'name="{name}".*?value="([^"]*)"', html)
            if m:
                fields[name] = m.group(1)
        return fields

    def _extract_hidden_fields(self, html: str) -> dict:
        """提取所有隐藏表单字段"""
        fields = {}
        for m in re.finditer(
            r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"',
            html, re.I
        ):
            fields[m.group(1)] = m.group(2)
        return fields

    def _ensure_logged_in(self):
        if not self._logged_in:
            self.login()

    # ------------------------------------------------------------------
    # 1. 认证
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """登录系统，返回是否成功"""
        # 获取登录页面
        resp = self._get(f"{self.BASE_URL}/Login.aspx")
        fields = self._extract_viewstate(resp.text)

        # 填充登录参数
        fields["userIdCard"] = self.username
        fields["userPwd"] = self.password
        fields["loginsubmit"] = "登 录"
        fields["myteip"] = "172.28.222.133--2"

        resp2 = self._post(f"{self.BASE_URL}/default.aspx", data=fields)

        if "Wjxt_UI" in resp2.text or "window.open" in resp2.text.lower():
            self._logged_in = True
            return True

        self._logged_in = "userIdCard" not in resp2.text and len(resp2.text) < 5000
        return self._logged_in

    def logout(self) -> bool:
        """退出登录"""
        self._ensure_logged_in()
        resp = self._get(f"{self.WJXT_UI}/Exiting.aspx",
                         headers={"Referer": f"{self.WJXT_UI}/default.aspx"})
        self._logged_in = False
        return resp.status_code == 200

    # ------------------------------------------------------------------
    # 2. 主页 & 导航
    # ------------------------------------------------------------------

    def get_main_page(self) -> str:
        """获取主应用框架页面 HTML"""
        self._ensure_logged_in()
        resp = self._get(f"{self.WJXT_UI}/default.aspx")
        return resp.text

    def get_sidebar(self) -> str:
        """获取左侧导航栏 HTML (WebUI.aspx?id=2)"""
        self._ensure_logged_in()
        resp = self._get(f"{self.WJXT_UI}/WebUI.aspx?id=2",
                         headers={"Referer": f"{self.WJXT_UI}/default.aspx"})
        return resp.text

    def get_department_list(self) -> str:
        """获取部门列表页面 HTML (WebUI.aspx?id=4)"""
        self._ensure_logged_in()
        resp = self._get(f"{self.WJXT_UI}/WebUI.aspx?id=4",
                         headers={"Referer": f"{self.WJXT_UI}/default.aspx"})
        return resp.text

    def get_departments(self) -> list[dict]:
        """解析部门列表，返回 [{id, name, type, url}, ...]"""
        html = self.get_department_list()
        depts = []
        for m in re.finditer(
            r"Right\.aspx\?id=(\d+)&type=(\d+)&tn=([^\"']+)",
            html, re.I
        ):
            depts.append({
                "id": int(m.group(1)),
                "type": int(m.group(2)),
                "tn_encoded": m.group(3),
                "tn_decoded": unquote(m.group(3), encoding="gb2312"),
                "url": f"{self.WJXT_UI}/Right.aspx?id={m.group(1)}&type={m.group(2)}&tn={m.group(3)}",
            })
        # 去重
        seen = set()
        unique = []
        for d in depts:
            key = d["id"]
            if key not in seen:
                seen.add(key)
                unique.append(d)
        return unique

    # ------------------------------------------------------------------
    # 3. 文件列表
    # ------------------------------------------------------------------

    def get_all_files(self) -> str:
        """获取全部文件列表页面 HTML (qstwj.aspx)"""
        self._ensure_logged_in()
        # 需要先访问主框架页以建立上下文
        self._get(f"{self.WJXT_UI}/default.aspx",
                  headers={"Referer": self.BASE_URL})
        self._get(f"{self.WJXT_UI}/WebUI.aspx?id=4",
                  headers={"Referer": f"{self.WJXT_UI}/default.aspx"})
        resp = self._get(f"{self.WJXT_UI}/qstwj.aspx",
                         headers={"Referer": f"{self.WJXT_UI}/WebUI.aspx?id=4"})
        return resp.text

    def get_file_list(self, list_id: int = 127, list_type: int = 100,
                      list_name: str = "全部文件",
                      page: int = 1) -> str:
        """获取分页文件列表 HTML (PageList.aspx)

        参数:
            list_id: 列表 ID，默认为 127
            list_type: 列表类型，默认为 100
            list_name: 列表名称，默认为 "全部文件"
            page: 页码，从 1 开始
        """
        self._ensure_logged_in()

        # 编码列表名称
        tn_encoded = quote(list_name, encoding="gb2312")
        base_url = (
            f"{self.WJXT_UI}/PageList.aspx"
            f"?id={list_id}&type={list_type}&tn={tn_encoded}"
        )

        # 设置上下文
        self._get(f"{self.WJXT_UI}/default.aspx")
        self._get(f"{self.WJXT_UI}/WebUI.aspx?id=4",
                  headers={"Referer": f"{self.WJXT_UI}/default.aspx"})

        if page <= 1:
            resp = self._get(base_url, headers={"Referer": f"{self.WJXT_UI}/WebUI.aspx?id=4"})
            return resp.text

        # 翻页：先获取首页拿到 VIEWSTATE，再模拟 __doPostBack
        resp1 = self._get(base_url)
        fields = self._extract_viewstate(resp1.text)
        fields["__EVENTTARGET"] = "AspNetPager1"
        fields["__EVENTARGUMENT"] = str(page)

        resp = self._post(base_url, data=fields,
                          headers={"Referer": base_url})
        return resp.text

    def get_dept_files(self, dept_id: int, dept_type: int = 0,
                       dept_name: str = "", page: int = 1) -> str:
        """获取部门文件列表 HTML (Right.aspx)

        参数:
            dept_id: 部门 ID
            dept_type: 类型，默认为 0
            dept_name: 部门名称 (中文)
            page: 页码，从 1 开始
        """
        self._ensure_logged_in()

        tn_encoded = quote(dept_name, encoding="gb2312") if dept_name else ""
        base_url = (
            f"{self.WJXT_UI}/Right.aspx"
            f"?id={dept_id}&type={dept_type}&tn={tn_encoded}"
        )

        self._get(f"{self.WJXT_UI}/default.aspx")
        self._get(f"{self.WJXT_UI}/WebUI.aspx?id=4",
                  headers={"Referer": f"{self.WJXT_UI}/default.aspx"})

        if page <= 1:
            resp = self._get(base_url)
            return resp.text

        resp1 = self._get(base_url)
        fields = self._extract_viewstate(resp1.text)
        fields["__EVENTTARGET"] = "AspNetPager1"
        fields["__EVENTARGUMENT"] = str(page)

        resp = self._post(base_url, data=fields,
                          headers={"Referer": base_url})
        return resp.text

    def parse_file_list(self, html: str) -> list[dict]:
        """解析文件列表 HTML，返回结构化数据"""
        files = []
        soup = BeautifulSoup(html, "html.parser")
        grid = soup.find("table", id="GridFiles")
        if not grid:
            return files

        rows = grid.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # 提取索引号
            index_text = cells[0].get_text(strip=True)
            if not index_text or not index_text.startswith("["):
                continue

            file_id = None
            title = ""
            department = ""
            date_str = ""
            is_unread = False
            download_url = ""

            # 解析第2列：部门 + 文件标题链接
            cell2 = cells[1]
            link = cell2.find("a")
            if link and "showfile.aspx" in link.get("href", ""):
                href = link["href"]
                m = re.search(r"id=(\d+)", href)
                if m:
                    file_id = int(m.group(1))
                title = link.get_text(strip=True)
                download_url = urljoin(self.WJXT_UI, href)

            # 部门名称
            bold = cell2.find("b")
            if bold:
                department = bold.get_text(strip=True).rstrip(":")

            # 未读标记
            if "未读" in cell2.get_text():
                is_unread = True

            # 日期
            if len(cells) > 3:
                date_text = cells[3].get_text(strip=True)
                date_match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", date_text)
                if date_match:
                    date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"

            files.append({
                "id": file_id,
                "index": index_text.strip("[] "),
                "title": title,
                "department": department,
                "date": date_str,
                "is_unread": is_unread,
                "detail_url": download_url,
            })

        return files

    def get_pagination_info(self, html: str) -> dict:
        """从文件列表 HTML 中提取分页信息"""
        m = re.search(
            r"第(\d+)页/总(\d+)\s*页\s*每页(\d+)条/共(\d+)条",
            html
        )
        if m:
            return {
                "current_page": int(m.group(1)),
                "total_pages": int(m.group(2)),
                "per_page": int(m.group(3)),
                "total_items": int(m.group(4)),
            }
        return {}

    # ------------------------------------------------------------------
    # 4. 文件详情 & 下载
    # ------------------------------------------------------------------

    def get_file_detail(self, file_id: int) -> dict:
        """获取文件详情，包含下载链接

        返回: {title, download_urls, raw_html, ...}
        download_urls 为列表，每项为 {url, filename}
        另保留 download_url 字段兼容旧代码（取第一个附件）
        """
        self._ensure_logged_in()

        # 设置上下文
        self._get(f"{self.WJXT_UI}/default.aspx")
        self._get(f"{self.WJXT_UI}/qstwj.aspx",
                  headers={"Referer": f"{self.WJXT_UI}/default.aspx"})

        url = f"{self.WJXT_UI}/showfile.aspx?id={file_id}"
        resp = self._get(url, headers={"Referer": f"{self.WJXT_UI}/qstwj.aspx"})

        result = {
            "file_id": file_id,
            "detail_url": url,
            "raw_html": resp.text,
            "download_urls": [],
            "title": "",
        }

        # 提取标题
        title_m = re.search(r"document\.title\s*=\s*'([^']*)'", resp.text)
        if title_m:
            result["title"] = title_m.group(1)

        # 提取所有附件链接（含 download 属性中的文件名）
        seen = set()
        attachments = []
        for m in re.finditer(
            r'<a[^>]*href="(/filezip/uploadfile/[^"]*)"[^>]*>',
            resp.text, re.I
        ):
            full_url = self.BASE_URL + m.group(1)
            if full_url in seen:
                continue
            seen.add(full_url)

            # 提取 download 属性中的原始文件名
            tag = m.group(0)
            dl_name = re.search(r'download="([^"]*)"', tag)
            filename = dl_name.group(1) if dl_name else os.path.basename(m.group(1))
            attachments.append({"url": full_url, "filename": filename})

        result["download_urls"] = attachments

        # 兼容旧代码：download_url 指向第一个附件
        if attachments:
            result["download_url"] = attachments[0]["url"]

        return result

    def download_file(self, file_id: int = None, url: str = None,
                      save_dir: str = ".") -> str | None:
        """下载文件，返回保存路径

        用法:
            client.download_file(file_id=61424)  # 按文件 ID 下载
            client.download_file(url="/filezip/uploadfile/2026/05/xxx.xlsx")  # 按 URL 下载
        """
        self._ensure_logged_in()

        if file_id:
            detail = self.get_file_detail(file_id)
            if not detail["download_url"]:
                return None
            url = detail["download_url"]

        if not url:
            return None

        if url.startswith("/"):
            url = self.BASE_URL + url

        resp = self._get(url, headers={"Referer": f"{self.WJXT_UI}/showfile.aspx"})

        filename = os.path.basename(url.split("?")[0])
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(resp.content)

        return filepath

    # ------------------------------------------------------------------
    # 5. 搜索
    # ------------------------------------------------------------------

    def search_files(self, keyword: str = "",
                     search_type: str = "title") -> str:
        """搜索文件 (search.aspx)

        注意: 该功能目前可能处于维护状态
        """
        self._ensure_logged_in()
        self._get(f"{self.WJXT_UI}/default.aspx")
        self._get(f"{self.WJXT_UI}/WebUI.aspx?id=2")

        url = f"{self.WJXT_UI}/search.aspx"
        resp = self._get(url, headers={"Referer": f"{self.WJXT_UI}/WebUI.aspx?id=2"})
        return resp.text

    def file_search(self, keyword: str = "") -> str:
        """文件高级搜索 (filesearch.aspx)

        注意: 该功能目前可能处于维护状态
        """
        self._ensure_logged_in()
        url = f"{self.WJXT_UI}/filesearch.aspx"
        resp = self._get(url)
        return resp.text

    # ------------------------------------------------------------------
    # 6. 用户管理
    # ------------------------------------------------------------------

    def get_password_page(self) -> str:
        """获取修改密码页面 HTML"""
        self._ensure_logged_in()
        resp = self._get(f"{self.WJXT_UI}/userEditPss.aspx",
                         headers={"Referer": f"{self.WJXT_UI}/default.aspx"})
        return resp.text

    def change_password(self, old_password: str,
                        new_password: str) -> bool:
        """修改密码

        密码要求: 必须包含大、小写字母、数字、特殊字符，长度 8-30 位
        """
        self._ensure_logged_in()

        # 获取密码修改页面
        resp1 = self._get(f"{self.WJXT_UI}/userEditPss.aspx")
        fields = self._extract_viewstate(resp1.text)
        fields.update(self._extract_hidden_fields(resp1.text))

        fields["oldPwd"] = old_password
        fields["userPWD1"] = new_password
        fields["userPWD2"] = new_password

        resp2 = self._post(f"{self.WJXT_UI}/userEditPss.aspx", data=fields,
                           headers={"Referer": f"{self.WJXT_UI}/userEditPss.aspx"})

        # 检查是否成功（通常成功后会有提示信息）
        return "成功" in resp2.text or "修改成功" in resp2.text

    # ------------------------------------------------------------------
    # 7. 电话簿
    # ------------------------------------------------------------------

    def get_phone_list(self) -> str:
        """获取内部电话簿 HTML"""
        self._ensure_logged_in()
        self._get(f"{self.WJXT_UI}/default.aspx")
        resp = self._get(f"{self.WJXT_UI}/phoneList.aspx",
                         headers={"Referer": f"{self.WJXT_UI}/default.aspx"})
        return resp.text

    def parse_phone_list(self, html: str = None) -> list[dict]:
        """解析电话簿，返回 [{name, phone, department, ...}]"""
        if html is None:
            html = self.get_phone_list()

        soup = BeautifulSoup(html, "html.parser")
        contacts = []

        # 尝试查找 GridView 表格
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    text_cells = [c.get_text(strip=True) for c in cells]
                    text_cells = [t for t in text_cells if t and t != "\xa0"]
                    if len(text_cells) >= 2:
                        contacts.append({
                            "name": text_cells[0] if len(text_cells) > 0 else "",
                            "phone": text_cells[1] if len(text_cells) > 1 else "",
                            "extra": " | ".join(text_cells[2:]) if len(text_cells) > 2 else "",
                        })

        return contacts

    # ------------------------------------------------------------------
    # 8. 业务办理
    # ------------------------------------------------------------------

    def get_todo_list(self) -> str:
        """获取待办列表 HTML"""
        self._ensure_logged_in()
        url = f"{self.BASE_URL}/business/business_mytodolists.aspx"
        resp = self._get(url, headers={"Referer": f"{self.WJXT_UI}/default.aspx"})
        return resp.text

    def get_todo_processing(self) -> str:
        """获取待办处理页面 HTML (business_DoList.aspx)"""
        self._ensure_logged_in()
        url = f"{self.BASE_URL}/business/business_DoList.aspx"
        resp = self._get(url, headers={"Referer": f"{self.BASE_URL}/business/business_mytodolists.aspx"})
        return resp.text

    def get_my_todo_lists(self) -> str:
        """获取我的待办列表 HTML"""
        self._ensure_logged_in()
        url = f"{self.BASE_URL}/business/business_MyToDoLists.aspx"
        resp = self._get(url, headers={"Referer": f"{self.BASE_URL}/business/business_mytodolists.aspx"})
        return resp.text

    def get_my_update_lists(self) -> str:
        """获取我的更新列表 HTML"""
        self._ensure_logged_in()
        url = f"{self.BASE_URL}/business/business_MyUpLists.aspx"
        resp = self._get(url, headers={"Referer": f"{self.BASE_URL}/business/business_mytodolists.aspx"})
        return resp.text

    def get_business_add_page(self) -> str:
        """获取新增业务页面 HTML"""
        self._ensure_logged_in()
        url = f"{self.BASE_URL}/business/businessAdd.aspx"
        resp = self._get(url, headers={"Referer": f"{self.BASE_URL}/business/business_mytodolists.aspx"})
        return resp.text

    def add_business(self, form_data: dict) -> str:
        """提交新业务

        参数:
            form_data: 表单字段字典 (字段因业务类型而异)
        """
        self._ensure_logged_in()

        # 获取新增页面以获取 VIEWSTATE
        resp1 = self._get(f"{self.BASE_URL}/business/businessAdd.aspx")
        fields = self._extract_viewstate(resp1.text)
        fields.update(self._extract_hidden_fields(resp1.text))
        fields.update(form_data)

        resp2 = self._post(f"{self.BASE_URL}/business/businessAdd.aspx",
                           data=fields,
                           headers={"Referer": f"{self.BASE_URL}/business/businessAdd.aspx"})
        return resp2.text

    # ------------------------------------------------------------------
    # 9. 便捷方法
    # ------------------------------------------------------------------

    def get_all_files_structured(self, max_pages: int = None) -> list[dict]:
        """获取所有文件（自动翻页），返回结构化数据列表"""
        all_files = []

        html = self.get_file_list(page=1)
        page_info = self.get_pagination_info(html)
        files = self.parse_file_list(html)
        all_files.extend(files)

        total_pages = page_info.get("total_pages", 1)
        if max_pages:
            total_pages = min(total_pages, max_pages)

        for p in range(2, total_pages + 1):
            html = self.get_file_list(page=p)
            files = self.parse_file_list(html)
            all_files.extend(files)

        return all_files

    def get_dept_files_structured(self, dept_id: int, dept_name: str = "",
                                  max_pages: int = None) -> list[dict]:
        """获取部门所有文件（自动翻页），返回结构化数据列表"""
        all_files = []

        html = self.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=1)
        page_info = self.get_pagination_info(html)
        files = self.parse_file_list(html)
        all_files.extend(files)

        total_pages = page_info.get("total_pages", 1)
        if max_pages:
            total_pages = min(total_pages, max_pages)

        for p in range(2, total_pages + 1):
            html = self.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=p)
            files = self.parse_file_list(html)
            all_files.extend(files)

        return all_files
