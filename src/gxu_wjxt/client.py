"""广西大学文件管理系统 同步客户端"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urljoin

import httpx

from .config import WjxtConfig
from .exceptions import AuthError, NetworkError, SessionExpiredError
from .types import FileInfo, FileDetail, DepartmentInfo, PhoneContact, PaginationInfo, SearchParams, SearchResult
from . import _base


class WjxtClient:
    """同步 HTTP 客户端

    用法:
        client = WjxtClient(username="学号", password="密码")
        client.login()
        files = list(client.iter_files())
    """

    def __init__(self, username: str = "", password: str = "",
                 config: WjxtConfig | None = None, **kwargs):
        if config is None:
            config = WjxtConfig.from_env()
        self._config = config.merge_with(
            username=username or None,
            password=password or None,
            **kwargs,
        )

        self._http = httpx.Client(
            timeout=self._config.timeout,
            verify=self._config.verify_ssl,
            max_redirects=self._config.max_redirects,
            headers={"User-Agent": self._config.user_agent},
            follow_redirects=True,
        )
        self._logged_in = False

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        return self._config.base_url

    @property
    def wjxt_ui(self) -> str:
        return f"{self._config.base_url}/Wjxt_UI"

    @property
    def logged_in(self) -> bool:
        return self._logged_in

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs) -> httpx.Response:
        try:
            resp = self._http.get(url, **kwargs)
        except httpx.RequestError as e:
            raise NetworkError(f"GET {url} 失败: {e}") from e
        resp.encoding = resp.charset_encoding or "gb2312"
        return resp

    def _post(self, url: str, data: dict = None, **kwargs) -> httpx.Response:
        try:
            resp = self._http.post(url, data=data, **kwargs)
        except httpx.RequestError as e:
            raise NetworkError(f"POST {url} 失败: {e}") from e
        resp.encoding = resp.charset_encoding or "gb2312"
        return resp

    def _ensure_logged_in(self):
        if not self._logged_in:
            self.login()

    def close(self):
        """关闭 HTTP 客户端"""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # 1. 认证
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """登录系统"""
        try:
            resp = self._get(f"{self.base_url}/Login.aspx")
            fields = _base.extract_viewstate(resp.text)

            fields["userIdCard"] = self._config.username
            fields["userPwd"] = self._config.password
            fields["loginsubmit"] = "登 录"
            fields["myteip"] = self._config.myteip

            resp2 = self._post(f"{self.base_url}/default.aspx", data=fields)

            if "Wjxt_UI" in resp2.text or "window.open" in resp2.text.lower():
                self._logged_in = True
                return True

            self._logged_in = (
                "userIdCard" not in resp2.text and len(resp2.text) < 5000
            )
            return self._logged_in

        except NetworkError:
            raise
        except Exception as e:
            raise AuthError(f"登录失败: {e}") from e

    def logout(self) -> bool:
        """退出登录"""
        self._ensure_logged_in()
        resp = self._get(
            f"{self.wjxt_ui}/Exiting.aspx",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        )
        self._logged_in = False
        return resp.status_code == 200

    # ------------------------------------------------------------------
    # 2. 主页 & 导航
    # ------------------------------------------------------------------

    def get_main_page(self) -> str:
        self._ensure_logged_in()
        return self._get(f"{self.wjxt_ui}/default.aspx").text

    def get_sidebar(self) -> str:
        self._ensure_logged_in()
        return self._get(
            f"{self.wjxt_ui}/WebUI.aspx?id=2",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        ).text

    def get_department_list(self) -> str:
        self._ensure_logged_in()
        return self._get(
            f"{self.wjxt_ui}/WebUI.aspx?id=4",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        ).text

    def get_departments(self) -> list[DepartmentInfo]:
        """获取部门列表"""
        html = self.get_department_list()
        return _base.parse_departments(html, self.wjxt_ui)

    # ------------------------------------------------------------------
    # 3. 文件列表
    # ------------------------------------------------------------------

    def _setup_list_context(self):
        """建立文件列表所需的页面上下文"""
        self._get(f"{self.wjxt_ui}/default.aspx")
        self._get(
            f"{self.wjxt_ui}/WebUI.aspx?id=4",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        )

    def get_all_files(self) -> str:
        """获取全部文件列表页面 HTML"""
        self._ensure_logged_in()
        self._setup_list_context()
        return self._get(
            f"{self.wjxt_ui}/qstwj.aspx",
            headers={"Referer": f"{self.wjxt_ui}/WebUI.aspx?id=4"},
        ).text

    def get_file_list(self, list_id: int = 127, list_type: int = 100,
                      list_name: str = "全部文件",
                      page: int = 1) -> str:
        """获取分页文件列表 HTML"""
        self._ensure_logged_in()

        tn_encoded = _base.encode_gb2312(list_name)
        base_url = (
            f"{self.wjxt_ui}/PageList.aspx"
            f"?id={list_id}&type={list_type}&tn={tn_encoded}"
        )

        self._setup_list_context()

        if page <= 1:
            return self._get(
                base_url,
                headers={"Referer": f"{self.wjxt_ui}/WebUI.aspx?id=4"},
            ).text

        resp1 = self._get(base_url)
        fields = _base.extract_viewstate(resp1.text)
        fields["__EVENTTARGET"] = "AspNetPager1"
        fields["__EVENTARGUMENT"] = str(page)

        return self._post(base_url, data=fields,
                          headers={"Referer": base_url}).text

    def get_dept_files(self, dept_id: int, dept_type: int = 0,
                       dept_name: str = "", page: int = 1) -> str:
        """获取部门文件列表 HTML"""
        self._ensure_logged_in()

        tn_encoded = _base.encode_gb2312(dept_name)
        base_url = (
            f"{self.wjxt_ui}/Right.aspx"
            f"?id={dept_id}&type={dept_type}&tn={tn_encoded}"
        )

        self._setup_list_context()

        if page <= 1:
            return self._get(base_url).text

        resp1 = self._get(base_url)
        fields = _base.extract_viewstate(resp1.text)
        fields["__EVENTTARGET"] = "AspNetPager1"
        fields["__EVENTARGUMENT"] = str(page)

        return self._post(base_url, data=fields,
                          headers={"Referer": base_url}).text

    # ------------------------------------------------------------------
    # 3b. 文件列表生成器 (惰性翻页)
    # ------------------------------------------------------------------

    def iter_files(self, max_pages: int = None) -> Iterator[FileInfo]:
        """惰性遍历全部文件列表（自动翻页）"""
        html = self.get_file_list(page=1)
        page_info = _base.parse_pagination_info(html)
        yield from _base.parse_file_list(html, self.wjxt_ui)

        total_pages = page_info.total_pages
        if max_pages:
            total_pages = min(total_pages, max_pages)

        for p in range(2, total_pages + 1):
            time.sleep(self._config.page_delay)
            html = self.get_file_list(page=p)
            yield from _base.parse_file_list(html, self.wjxt_ui)

    def iter_dept_files(self, dept_id: int, dept_name: str = "",
                        max_pages: int = None) -> Iterator[FileInfo]:
        """惰性遍历部门文件列表（自动翻页）"""
        html = self.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=1)
        page_info = _base.parse_pagination_info(html)
        yield from _base.parse_file_list(html, self.wjxt_ui)

        total_pages = page_info.total_pages
        if max_pages:
            total_pages = min(total_pages, max_pages)

        for p in range(2, total_pages + 1):
            time.sleep(self._config.page_delay)
            html = self.get_dept_files(dept_id=dept_id, dept_name=dept_name, page=p)
            yield from _base.parse_file_list(html, self.wjxt_ui)

    def get_file_list_structured(self, page: int = 1) -> tuple[list[FileInfo], PaginationInfo]:
        """单页文件列表 + 分页信息"""
        html = self.get_file_list(page=page)
        return _base.parse_file_list(html, self.wjxt_ui), _base.parse_pagination_info(html)

    # ------------------------------------------------------------------
    # 4. 文件详情 & 下载
    # ------------------------------------------------------------------

    def get_file_detail(self, file_id: int) -> FileDetail:
        """获取文件详情"""
        self._ensure_logged_in()

        self._get(f"{self.wjxt_ui}/default.aspx")
        self._get(
            f"{self.wjxt_ui}/qstwj.aspx",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        )

        url = f"{self.wjxt_ui}/showfile.aspx?id={file_id}"
        resp = self._get(
            url,
            headers={"Referer": f"{self.wjxt_ui}/qstwj.aspx"},
        )

        detail = _base.parse_file_detail(resp.text, file_id, url, self.base_url)
        return FileDetail(
            file_id=detail["file_id"],
            title=detail["title"],
            detail_url=detail["detail_url"],
            raw_html=detail["raw_html"],
            download_urls=detail["download_urls"],
        )

    def download_file(self, file_id: int = None, url: str = None,
                      save_dir: str = ".") -> str | None:
        """下载文件，返回保存路径"""
        self._ensure_logged_in()

        if file_id:
            detail = self.get_file_detail(file_id)
            if not detail.download_url:
                return None
            url = detail.download_url

        if not url:
            return None

        if url.startswith("/"):
            url = self.base_url + url

        resp = self._get(
            url,
            headers={"Referer": f"{self.wjxt_ui}/showfile.aspx"},
        )

        filename = os.path.basename(url.split("?")[0])
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(resp.content)

        return filepath

    # ------------------------------------------------------------------
    # 5. 搜索
    # ------------------------------------------------------------------

    def _get_search_viewstate(self) -> dict:
        """获取搜索表单所需的 VIEWSTATE（来自侧边栏）"""
        self._get(f"{self.wjxt_ui}/default.aspx")
        r = self._get(
            f"{self.wjxt_ui}/WebUI.aspx?id=2",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        )
        r.encoding = "gbk"
        fields = {}
        fields.update(_base.extract_viewstate(r.text))
        fields.update(_base.extract_hidden_fields(r.text))
        return fields

    def _search_post(self, url: str, fields: dict) -> str:
        """POST 搜索请求（使用 GB2312 编码）"""
        body = _base.encode_post_data_gb2312(fields)
        resp = self._http.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{self.wjxt_ui}/WebUI.aspx?id=2",
            },
        )
        resp.encoding = "gbk"
        return resp.text

    def search(self, params: SearchParams = None, *,
               page: int = 1, **kwargs) -> SearchResult:
        """执行文件搜索并返回结构化结果

        Args:
            params: SearchParams 实例，也可直接传关键字参数构造
                例如: client.search(keyword=\"奖学金\", search_type=\"title\")
            page: 页码（从 1 开始）

        Returns:
            SearchResult 包含当前页文件列表、总记录数、分页信息
        """
        if params is None:
            params = SearchParams(**kwargs)
        elif kwargs:
            for k, v in kwargs.items():
                if hasattr(params, k) and v is not None:
                    setattr(params, k, v)

        self._ensure_logged_in()

        # 构建搜索表单（使用 GB2312 编码确保中文关键字被正确解析）
        fields = self._get_search_viewstate()
        fields["content"] = params.keyword
        fields["searchType"] = params.search_type
        fields["filetype"] = params.file_type
        fields["fileTime"] = params.file_year
        fields["AccurateFuzzy"] = params.match_mode

        search_url = f"{self.wjxt_ui}/search.aspx"

        if page <= 1:
            fields["__EVENTTARGET"] = "Button1"
            fields["__EVENTARGUMENT"] = ""
            html = self._search_post(search_url, fields)
        else:
            # 先执行搜索获得第 1 页的 VIEWSTATE
            fields["__EVENTTARGET"] = "Button1"
            fields["__EVENTARGUMENT"] = ""
            html_p1 = self._search_post(search_url, dict(fields))
            vs = _base.extract_viewstate(html_p1)
            vs.update(_base.extract_hidden_fields(html_p1))
            # 翻页参数不含中文，使用标准 POST
            vs["__EVENTTARGET"] = "AspNetPager1"
            vs["__EVENTARGUMENT"] = str(page)
            resp = self._post(
                search_url, data=vs,
                headers={"Referer": search_url},
            )
            resp.encoding = "gbk"
            html = resp.text

        files = _base.parse_search_results(html, self.wjxt_ui)
        total_count = _base.parse_search_record_count(html)
        per_page = 50
        total_pages = max(1, (total_count + per_page - 1) // per_page)

        return SearchResult(
            files=files,
            total_count=total_count,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
        )

    def iter_search(self, params: SearchParams = None,
                    max_pages: int = None, **kwargs) -> Iterator[FileInfo]:
        """惰性搜索遍历全部结果（自动翻页）

        Args:
            params: SearchParams 实例
            max_pages: 最多翻页数，None 表示翻完所有页
            **kwargs: 直接传搜索参数

        Yields:
            FileInfo 逐个产出
        """
        result = self.search(params=params, page=1, **kwargs)
        yield from result.files

        total_pages = result.total_pages
        if max_pages:
            total_pages = min(total_pages, max_pages)

        for p in range(2, total_pages + 1):
            time.sleep(self._config.page_delay)
            page_result = self.search(params=params, page=p, **kwargs)
            yield from page_result.files

    # 保留旧接口（向后兼容，返回结构化结果）
    def search_files(self, keyword: str = "",
                     search_type: str = "title") -> SearchResult:
        """简单搜索（已升级为完整搜索）"""
        return self.search(keyword=keyword, search_type=search_type)

    def file_search(self, keyword: str = "") -> SearchResult:
        """高级搜索（已升级为完整搜索）"""
        return self.search(keyword=keyword)

    # ------------------------------------------------------------------
    # 6. 用户管理
    # ------------------------------------------------------------------

    def get_password_page(self) -> str:
        """获取修改密码页面 HTML"""
        self._ensure_logged_in()
        return self._get(
            f"{self.wjxt_ui}/userEditPss.aspx",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        ).text

    def change_password(self, old_password: str,
                        new_password: str) -> bool:
        """修改密码"""
        self._ensure_logged_in()

        resp1 = self._get(f"{self.wjxt_ui}/userEditPss.aspx")
        fields = _base.extract_viewstate(resp1.text)
        fields.update(_base.extract_hidden_fields(resp1.text))

        fields["oldPwd"] = old_password
        fields["userPWD1"] = new_password
        fields["userPWD2"] = new_password

        resp2 = self._post(
            f"{self.wjxt_ui}/userEditPss.aspx",
            data=fields,
            headers={"Referer": f"{self.wjxt_ui}/userEditPss.aspx"},
        )

        return "成功" in resp2.text or "修改成功" in resp2.text

    # ------------------------------------------------------------------
    # 7. 电话簿
    # ------------------------------------------------------------------

    def get_phone_list(self) -> str:
        """获取电话簿 HTML"""
        self._ensure_logged_in()
        self._get(f"{self.wjxt_ui}/default.aspx")
        return self._get(
            f"{self.wjxt_ui}/phoneList.aspx",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        ).text

    def parse_phone_list(self, html: str = None) -> list[PhoneContact]:
        """解析电话簿"""
        if html is None:
            html = self.get_phone_list()
        return _base.parse_phone_list(html)

    # ------------------------------------------------------------------
    # 8. 业务办理
    # ------------------------------------------------------------------

    def get_todo_list(self) -> str:
        self._ensure_logged_in()
        return self._get(
            f"{self.base_url}/business/business_mytodolists.aspx",
            headers={"Referer": f"{self.wjxt_ui}/default.aspx"},
        ).text

    def get_todo_processing(self) -> str:
        self._ensure_logged_in()
        return self._get(
            f"{self.base_url}/business/business_DoList.aspx",
            headers={"Referer": f"{self.base_url}/business/business_mytodolists.aspx"},
        ).text

    def get_my_todo_lists(self) -> str:
        self._ensure_logged_in()
        return self._get(
            f"{self.base_url}/business/business_MyToDoLists.aspx",
            headers={"Referer": f"{self.base_url}/business/business_mytodolists.aspx"},
        ).text

    def get_my_update_lists(self) -> str:
        self._ensure_logged_in()
        return self._get(
            f"{self.base_url}/business/business_MyUpLists.aspx",
            headers={"Referer": f"{self.base_url}/business/business_mytodolists.aspx"},
        ).text

    def get_business_add_page(self) -> str:
        self._ensure_logged_in()
        return self._get(
            f"{self.base_url}/business/businessAdd.aspx",
            headers={"Referer": f"{self.base_url}/business/business_mytodolists.aspx"},
        ).text

    def add_business(self, form_data: dict) -> str:
        """提交新业务"""
        self._ensure_logged_in()

        resp1 = self._get(f"{self.base_url}/business/businessAdd.aspx")
        fields = _base.extract_viewstate(resp1.text)
        fields.update(_base.extract_hidden_fields(resp1.text))
        fields.update(form_data)

        return self._post(
            f"{self.base_url}/business/businessAdd.aspx",
            data=fields,
            headers={"Referer": f"{self.base_url}/business/businessAdd.aspx"},
        ).text
