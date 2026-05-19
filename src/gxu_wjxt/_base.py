"""内部共享工具 — 供 sync 和 async client 共用"""

import re
import hashlib
from urllib.parse import quote, unquote, urljoin

from bs4 import BeautifulSoup

from .types import FileInfo, PaginationInfo, PhoneContact, DepartmentInfo


def extract_viewstate(html: str) -> dict:
    """提取 ASP.NET 隐藏表单字段"""
    fields = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR",
                 "__SCROLLPOSITIONX", "__SCROLLPOSITIONY",
                 "__EVENTTARGET", "__EVENTARGUMENT"):
        m = re.search(rf'name="{name}".*?value="([^"]*)"', html)
        if m:
            fields[name] = m.group(1)
    return fields


def extract_hidden_fields(html: str) -> dict:
    """提取所有隐藏表单字段"""
    fields = {}
    for m in re.finditer(
        r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"',
        html, re.I
    ):
        fields[m.group(1)] = m.group(2)
    return fields


def encode_gb2312(name: str) -> str:
    """将字符串编码为 GB2312 的 URL 编码形式"""
    return quote(name, encoding="gb2312") if name else ""


def decode_gb2312(encoded: str) -> str:
    """解码 GB2312 的 URL 编码"""
    return unquote(encoded, encoding="gb2312") if encoded else ""


def encode_post_data_gb2312(fields: dict) -> str:
    """将表单字段编码为 GB2312 URL-encoded POST body

    ASP.NET 服务器端使用 GB2312 解析表单数据，若用 UTF-8 提交中文
    关键字会导致搜索无结果。此函数对所有字段名和字段值做 GB2312 编码。
    """
    return "&".join(
        f"{quote(k, encoding='gb2312')}={quote(v, encoding='gb2312')}"
        for k, v in fields.items()
    )


def parse_file_list(html: str, base_url: str) -> list[FileInfo]:
    """解析文件列表 HTML，返回 FileInfo 列表"""
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

        index_text = cells[0].get_text(strip=True)
        if not index_text or not index_text.startswith("["):
            continue

        file_id = None
        title = ""
        department = ""
        date_str = ""
        is_unread = False
        download_url = ""

        cell2 = cells[1]
        link = cell2.find("a")
        if link and "showfile.aspx" in link.get("href", ""):
            href = link["href"]
            m = re.search(r"id=(\d+)", href)
            if m:
                file_id = int(m.group(1))
            title = link.get_text(strip=True)
            download_url = urljoin(base_url, href)

        bold = cell2.find("b")
        if bold:
            department = bold.get_text(strip=True).rstrip(":")

        if "未读" in cell2.get_text():
            is_unread = True

        if len(cells) > 3:
            date_text = cells[3].get_text(strip=True)
            date_match = re.search(
                r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", date_text
            )
            if date_match:
                date_str = (
                    f"{date_match.group(1)}-"
                    f"{date_match.group(2).zfill(2)}-"
                    f"{date_match.group(3).zfill(2)}"
                )

        files.append(FileInfo(
            id=file_id,
            index=index_text.strip("[] "),
            title=title,
            department=department,
            date=date_str,
            is_unread=is_unread,
            detail_url=download_url,
        ))

    return files


def parse_pagination_info(html: str) -> PaginationInfo:
    """从文件列表 HTML 中提取分页信息"""
    m = re.search(
        r"第(\d+)页/总(\d+)\s*页\s*每页(\d+)条/共(\d+)条",
        html
    )
    if m:
        return PaginationInfo(
            current_page=int(m.group(1)),
            total_pages=int(m.group(2)),
            per_page=int(m.group(3)),
            total_items=int(m.group(4)),
        )
    return PaginationInfo()


def parse_departments(html: str, wjxt_ui_url: str) -> list[DepartmentInfo]:
    """解析部门列表"""
    depts = []
    for m in re.finditer(
        r"Right\.aspx\?id=(\d+)&type=(\d+)&tn=([^\"']+)",
        html, re.I
    ):
        depts.append(DepartmentInfo(
            id=int(m.group(1)),
            type=int(m.group(2)),
            tn_encoded=m.group(3),
            tn_decoded=decode_gb2312(m.group(3)),
            url=f"{wjxt_ui_url}/Right.aspx?id={m.group(1)}&type={m.group(2)}&tn={m.group(3)}",
        ))

    seen = set()
    unique = []
    for d in depts:
        if d.id not in seen:
            seen.add(d.id)
            unique.append(d)
    return unique


def parse_phone_list(html: str) -> list[PhoneContact]:
    """解析电话簿"""
    soup = BeautifulSoup(html, "html.parser")
    contacts = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2:
                text_cells = [c.get_text(strip=True) for c in cells]
                text_cells = [t for t in text_cells if t and t != "\xa0"]
                if len(text_cells) >= 2:
                    contacts.append(PhoneContact(
                        name=text_cells[0] if len(text_cells) > 0 else "",
                        phone=text_cells[1] if len(text_cells) > 1 else "",
                        extra=" | ".join(text_cells[2:]) if len(text_cells) > 2 else "",
                    ))

    return contacts


def parse_search_results(html: str, base_url: str) -> list[FileInfo]:
    """解析搜索结果页的 GridFiles 表"""
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

        index_cell = cells[0].get_text(strip=True)
        if not index_cell or not index_cell.startswith("["):
            continue

        file_id = None
        title = ""
        department = ""
        date_str = ""
        is_unread = False

        content_cell = cells[1]
        link = content_cell.find("a")
        if link:
            href = link.get("href", "")
            m = re.search(r"id=(\d+)", href)
            if m:
                file_id = int(m.group(1))
            title = link.get_text(strip=True)

        bold = content_cell.find("b")
        if bold:
            department = bold.get_text(strip=True).rstrip(":")

        if "未读" in content_cell.get_text():
            is_unread = True

        if len(cells) > 3:
            date_match = re.search(
                r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
                cells[3].get_text()
            )
            if date_match:
                date_str = (
                    f"{date_match.group(1)}-"
                    f"{date_match.group(2).zfill(2)}-"
                    f"{date_match.group(3).zfill(2)}"
                )

        detail_url = f"{base_url}/showfile.aspx?id={file_id}" if file_id else ""

        files.append(FileInfo(
            id=file_id,
            index=index_cell.strip("[] "),
            title=title,
            department=department,
            date=date_str,
            is_unread=is_unread,
            detail_url=detail_url,
        ))

    return files


def parse_search_record_count(html: str) -> int:
    """从搜索结果的 showtype 中提取 '共XXXX条' 的记录总数"""
    m = re.search(r"共(\d+)条", html)
    return int(m.group(1)) if m else 0


def safe_filename(name: str, max_len: int = 120) -> str:
    """去除文件名中的非法字符"""
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


def file_hash(file_id: int) -> str:
    """生成文件唯一标识"""
    return hashlib.md5(f"wjxt_file_{file_id}".encode()).hexdigest()


def parse_file_detail(html: str, file_id: int, detail_url: str,
                      base_url: str) -> dict:
    """解析文件详情页，返回 {title, download_urls, ...}"""
    from .types import Attachment

    result = {
        "file_id": file_id,
        "detail_url": detail_url,
        "raw_html": html,
        "download_urls": [],
        "title": "",
    }

    title_m = re.search(r"document\.title\s*=\s*'([^']*)'", html)
    if title_m:
        result["title"] = title_m.group(1)

    seen = set()
    attachments = []
    for m in re.finditer(
        r'<a[^>]*href="(/filezip/uploadfile/[^"]*)"[^>]*>',
        html, re.I
    ):
        full_url = base_url + m.group(1)
        if full_url in seen:
            continue
        seen.add(full_url)

        tag = m.group(0)
        dl_name = re.search(r'download="([^"]*)"', tag)
        filename = dl_name.group(1) if dl_name else m.group(1).rsplit("/", 1)[-1]
        attachments.append(Attachment(url=full_url, filename=filename))

    result["download_urls"] = attachments
    result["download_url"] = attachments[0].url if attachments else ""
    return result
