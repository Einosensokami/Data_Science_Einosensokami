"""第 4 題：搜尋博客來的「演算法」書籍並輸出 booklist.csv。

以可見 Chrome 依序開啟各頁搜尋結果網址，逐頁抓取書籍資料。
"""

from __future__ import annotations

import csv
import random
import re
import time
from pathlib import Path
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


KEYWORD = "演算法"
URL_TEMPLATE = (
    "https://search.books.com.tw/search/query/"
    "cat/all/sort/1/v/1/spell/3/page/{page}/key/{keyword}"
)
OUTPUT = Path(__file__).with_name("booklist.csv")
WAIT_SECONDS = 20
MAX_PAGES = 50  # 僅供 scrape_legacy 相容保留；正式流程會讀取網站總頁數。
ERROR_PAGE_MARKERS = ("Connection is temporarily unavailable", "連線暫時異常")

PRODUCT_SELECTOR = "div[id^='prod-itemlist-']:not([id^='prod-itemlist-footer-'])"
PRODUCT_LINK_SELECTOR = "a[href*='/redirect/move/'][href*='/item/']"


def clean(text: str) -> str:
    """將換行與連續空白整理成一個空白。"""
    return re.sub(r"\s+", " ", text).strip()


def product_container(link: Tag) -> Tag:
    """從商品連結往上尋找一筆搜尋結果的容器。"""
    for parent in link.parents:
        if not isinstance(parent, Tag):
            continue
        classes = " ".join(parent.get("class", []))
        if parent.get("id", "").startswith("prod-itemlist-"):
            return parent
        if any(name in classes for name in ("searchbook", "search_book", "mod_search")):
            return parent
        if parent.name in {"article", "li"} and "作者" in parent.get_text(" ", strip=True):
            return parent
    return link.parent if isinstance(link.parent, Tag) else link


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.S)
    return clean(match.group(1)) if match else ""


def parse_book(item: Tag, link: Tag) -> dict[str, str] | None:
    title = clean(link.get_text(" ", strip=True))
    if not title:
        return None

    text = clean(item.get_text(" ", strip=True))
    # 博客來搜尋結果會以「作者：」顯示作者；到下一個欄位名稱或價格前停止。
    author = first_match(
        r"作者[：:]\s*(.*?)(?=\s*(?:出版社|出版日期|ISBN|優惠價|定價|\d+折)\s*[：:]?|$)",
        text,
    )
    if author:
        author = re.sub(r"\s*(?:譯者|繪者)[：:].*", "", author)
    else:
        author_node = item.select_one(".author")
        author = clean(author_node.get_text(" ", strip=True)) if author_node else ""

    price = ""
    price_node = item.select_one(".price, .price_box, [class*='price']")
    if price_node:
        price_text = clean(price_node.get_text(" ", strip=True))
        # 保留網站原始價格文字，例如「優惠價：79折 379元」。
        price = first_match(r"(?:優惠價|定價)[：:]?\s*(.*)", price_text) or price_text
    if not price:
        price = first_match(
            r"(?:優惠價|定價)[：:]?\s*(.*?)(?=\s*(?:作者|出版社|出版日期)[：:]|$)",
            text,
        )

    return {
        "書名": title,
        "網址": product_url(link.get("href", "")),
        "作者": author,
        "書價": price,
    }


def product_url(href: str) -> str:
    """將搜尋頁的轉址網址還原為題目所需的正式商品網址。"""
    code = re.search(r"/item/([A-Za-z0-9]+)/", href)
    if code:
        return f"https://www.books.com.tw/products/{code.group(1)}"
    return urljoin("https://www.books.com.tw/", href)


def parse_search_page(html: str | bytes) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")

    rows: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    containers = soup.select(PRODUCT_SELECTOR)
    if containers:
        for item in containers:
            for link in item.select(PRODUCT_LINK_SELECTOR):
                href = link.get("href", "")
                full_url = product_url(href)
                if not href or full_url in seen_urls:
                    continue
                book = parse_book(item, link)
                if book is None:
                    continue
                seen_urls.add(full_url)
                rows.append(book)
                break
    else:
        for link in soup.select(PRODUCT_LINK_SELECTOR):
            href = link.get("href", "")
            full_url = product_url(href)
            if not href or full_url in seen_urls:
                continue
            book = parse_book(product_container(link), link)
            if book is None:
                continue
            seen_urls.add(full_url)
            rows.append(book)

    if not rows:
        raise RuntimeError("找不到書籍資料，博客來的搜尋結果版面可能已變更。")
    return rows


def parse_total_pages(html: str | bytes) -> int:
    """Read the last page number from the search-results summary."""
    soup = BeautifulSoup(html, "html.parser")
    for paragraph in soup.find_all("p"):
        text = clean(paragraph.get_text(" ", strip=True))
        match = re.search(
            r"搜尋結果共\s*[\d,]+\s*筆\s*[,，]?\s*頁數\s*\d+\s*/\s*(\d+)",
            text,
        )
        if match:
            total_pages = int(match.group(1))
            if total_pages > 0:
                return total_pages

    raise RuntimeError("找不到搜尋結果的總頁數，博客來的搜尋結果版面可能已變更。")


def page_is_blocked(driver: webdriver.Chrome) -> bool:
    """檢查是否被網站暫時阻擋。"""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return False
    return any(marker in body for marker in ERROR_PAGE_MARKERS)


def product_signature(driver: webdriver.Chrome) -> tuple[str, ...]:
    """取得目前頁面的商品連結，作為換頁是否成功的指紋。"""
    try:
        products = driver.find_elements(By.CSS_SELECTOR, PRODUCT_SELECTOR)
        hrefs: list[str] = []
        for product in products:
            links = product.find_elements(By.CSS_SELECTOR, PRODUCT_LINK_SELECTOR)
            if links:
                hrefs.append(links[0].get_attribute("href") or "")
        return tuple(hrefs)
    except Exception:
        return ()


def wait_for_products(
    driver: webdriver.Chrome,
    previous_signature: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """等待搜尋結果出現；換頁時需等待商品指紋改變。"""
    deadline = time.time() + WAIT_SECONDS
    while time.time() < deadline:
        if page_is_blocked(driver):
            raise RuntimeError("博客來暫時拒絕自動化瀏覽器，請稍後再執行。")
        signature = product_signature(driver)
        if signature and (previous_signature is None or signature != previous_signature):
            return signature
        time.sleep(0.5)

    if page_is_blocked(driver):
        raise RuntimeError("博客來暫時拒絕自動化瀏覽器，請稍後再執行。")
    raise RuntimeError("等待搜尋結果逾時，頁面未載入書籍。")


def scrape_legacy() -> list[dict[str, str]]:
    """每一頁重開可見 Chrome，依頁碼網址逐頁載入搜尋結果。"""
    options = Options()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--window-size=1440,1000")

    rows: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    page_size: int | None = None

    for page in range(1, MAX_PAGES + 1):
        page_url = URL_TEMPLATE.format(page=page, keyword=quote(KEYWORD))
        print(f"正在開啟瀏覽器抓取第 {page} 頁：{page_url}")
        driver = webdriver.Chrome(options=options)

        try:
            driver.get(page_url)
            try:
                wait_for_products(driver)
                page_rows = parse_search_page(driver.page_source)
            except RuntimeError as error:
                if page == 1 or page_is_blocked(driver):
                    raise
                print(f"第 {page} 頁無法取得商品（{error}），分頁結束。")
                break
        finally:
            driver.quit()
            print(f"第 {page} 頁瀏覽器已關閉。")

        new_count = 0
        for row in page_rows:
            product_page_url = row["網址"]
            if product_page_url in seen_urls:
                continue
            seen_urls.add(product_page_url)
            rows.append(row)
            new_count += 1

        print(
            f"第 {page} 頁：解析 {len(page_rows)} 筆，"
            f"新增 {new_count} 筆，累計 {len(rows)} 筆"
        )
        if new_count == 0:
            print("本頁沒有新增商品，分頁結束。")
            break

        if page_size is None:
            page_size = len(page_rows)
        elif len(page_rows) < page_size:
            print(
                f"第 {page} 頁只有 {len(page_rows)} 筆，少於每頁 {page_size} 筆，"
                "判定為最後一頁。"
            )
            break

        time.sleep(random.uniform(2, 4))
    else:
        raise RuntimeError(f"已達最大頁數上限 ({MAX_PAGES})，停止以避免無限迴圈。")

    return rows


def scrape() -> list[dict[str, str]]:
    """抓取第一頁的總頁數，再依該頁數逐頁抓取。"""
    options = Options()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--window-size=1440,1000")

    rows: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    page = 1
    total_pages: int | None = None

    while total_pages is None or page <= total_pages:
        page_url = URL_TEMPLATE.format(page=page, keyword=quote(KEYWORD))
        print(f"正在抓取第 {page} 頁：{page_url}")
        driver = webdriver.Chrome(options=options)
        try:
            driver.get(page_url)
            wait_for_products(driver)
            html = driver.page_source
            page_rows = parse_search_page(html)
            if total_pages is None:
                total_pages = parse_total_pages(html)
                print(f"搜尋結果共有 {total_pages} 頁，將依此頁數抓取。")
        finally:
            driver.quit()

        new_count = 0
        for row in page_rows:
            product_page_url = row["網址"]
            if product_page_url in seen_urls:
                continue
            seen_urls.add(product_page_url)
            rows.append(row)
            new_count += 1

        print(f"第 {page}/{total_pages} 頁：新增 {new_count} 筆，累計 {len(rows)} 筆。")
        page += 1
        if page <= total_pages:
            time.sleep(random.uniform(2, 4))

    return rows


def main() -> None:
    try:
        rows = scrape()
    except RuntimeError as error:
        raise SystemExit(f"停止：{error}") from None

    fields = ["書名", "網址", "作者", "書價"]
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"完成：{len(rows)} 本「{KEYWORD}」書籍，已儲存至 {OUTPUT.name}")


if __name__ == "__main__":
    main()
