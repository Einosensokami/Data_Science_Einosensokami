"""第 13 題：自動在 momo 搜尋 nba，將搜尋結果另存為 NBA_test.html。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://www.momoshop.com.tw/main/Main.jsp"
KEYWORD = "nba"
OUTPUT = Path(__file__).with_name("NBA_test.html")
SEARCH_INPUT = '[data-testid="header-search-input"]'
PRODUCT_NAME = "a.prdName"


def make_snapshot(html: str, source_url: str) -> tuple[str, int]:
    """保留已渲染的搜尋結果，讓 HTML 在本機開啟時仍能顯示。"""
    parsed = urlsplit(source_url)
    if parsed.hostname != "www.momoshop.com.tw" or unquote(parsed.path).rstrip("/").lower() != f"/search/{KEYWORD}":
        raise RuntimeError("目前頁面不是 nba 搜尋結果，未儲存 HTML。")
    soup = BeautifulSoup(html, "html.parser")
    products = soup.select(PRODUCT_NAME)
    if not products or any(not product.get_text(strip=True) for product in products):
        raise RuntimeError("搜尋結果尚未載入商品，未儲存 HTML。")
    if soup.head is None or soup.title is None or KEYWORD not in soup.title.get_text().lower():
        raise RuntimeError("搜尋結果的網頁標題或文件結構不完整。")

    # 移除動態程式，避免重新開啟本機 HTML 時，網站重新渲染成空白或錯誤頁。
    for element in soup.select('script, link[as="script"], base, meta[charset]'):
        element.decompose()
    charset = soup.new_tag("meta", charset="utf-8")
    base = soup.new_tag("base", href=source_url)
    soup.head.insert(0, base)
    soup.head.insert(0, charset)
    return str(soup), len(products)


def scrape(headless: bool = False) -> tuple[str, str, int]:
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--window-size=1440,1000")
    options.page_load_strategy = "eager"
    if headless:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(60)
        wait = WebDriverWait(driver, 30)
        driver.get(URL)
        search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SEARCH_INPUT)))
        search.clear()
        search.send_keys(KEYWORD, Keys.ENTER)
        wait.until(
            lambda browser: unquote(urlsplit(browser.current_url).path).rstrip("/").lower()
            == f"/search/{KEYWORD}"
        )
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, PRODUCT_NAME)))
        source_url = driver.current_url
        html, count = make_snapshot(driver.page_source, source_url)
        return html, source_url, count
    except TimeoutException:
        raise RuntimeError("等候 momo 搜尋頁逾時；網站可能尚未載入、要求驗證或已改版。") from None
    finally:
        driver.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="在背景執行 Chrome")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        html, source_url, count = scrape(args.headless)
    except (WebDriverException, RuntimeError) as error:
        raise SystemExit(f"抓取失敗，未覆蓋輸出檔：{error}") from None

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"搜尋關鍵字：{KEYWORD}")
    print(f"搜尋結果網址：{source_url}")
    print(f"已儲存本頁 {count} 筆商品的搜尋畫面至 {OUTPUT}")


if __name__ == "__main__":
    main()
