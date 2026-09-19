"""第 11 題：使用 Selenium 操作分頁，抓取全部 NBA 商品資料。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://fchart.github.io/ML/nba_items.html"
DIRECTORY = Path(__file__).resolve().parent
FIELDS = ["商品編號", "商品名稱", "價格"]
WAIT_SECONDS = 20


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_products(html: str) -> list[dict[str, str]]:
    """解析目前顯示的商品表格，並驗證每列都有三個必要欄位。"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("#our-table")
    if table is None:
        raise RuntimeError("找不到 NBA 商品表格。")

    rows: list[dict[str, str]] = []
    for row_number, row in enumerate(table.select("tbody tr"), 1):
        cells = [clean(cell.get_text(" ", strip=True)) for cell in row.select("td")]
        if len(cells) != len(FIELDS):
            raise RuntimeError(
                f"第 {row_number} 列預期有 {len(FIELDS)} 個欄位，實際取得 {len(cells)} 個。"
            )
        if not all(cells):
            raise RuntimeError(f"第 {row_number} 列含有空白的必要欄位。")
        rows.append(dict(zip(FIELDS, cells)))

    if not rows:
        raise RuntimeError("目前頁面沒有 NBA 商品資料。")
    return rows


def page_signature(driver: webdriver.Chrome) -> tuple[str, ...]:
    """取得目前表格列的文字，供分頁切換時判斷內容是否更新。"""
    return tuple(
        clean(row.get_attribute("textContent") or "")
        for row in driver.find_elements(By.CSS_SELECTOR, "#table-body tr")
    )


def collect_pages(driver: webdriver.Chrome) -> list[list[dict[str, str]]]:
    """從第一頁開始逐一按下一頁，直到分頁列不再提供 next 按鈕。"""
    wait = WebDriverWait(driver, WAIT_SECONDS)
    driver.get(URL)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#table-body tr")))

    pages: list[list[dict[str, str]]] = []
    seen_signatures: set[tuple[str, ...]] = set()

    while True:
        signature = page_signature(driver)
        if not signature or signature in seen_signatures:
            raise RuntimeError("分頁內容沒有更新，為避免重複抓取已停止。")
        seen_signatures.add(signature)
        pages.append(parse_products(driver.page_source))

        next_buttons = driver.find_elements(By.CSS_SELECTOR, "#pagination-wrapper .nextbtn")
        if not next_buttons:
            break

        next_button = next_buttons[0]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        wait.until(lambda _driver: next_button.is_displayed() and next_button.is_enabled())
        driver.execute_script("arguments[0].click();", next_button)
        wait.until(lambda current_driver: page_signature(current_driver) != signature)

    return pages


def output_path(page_number: int) -> Path:
    return DIRECTORY / f"NBA_Products{page_number}.csv"


def write_page(page_number: int, rows: list[dict[str, str]]) -> Path:
    path = output_path(page_number)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def remove_stale_outputs(last_page: int) -> None:
    """移除先前執行殘留、但本次已不存在的較高頁碼檔案。"""
    for path in DIRECTORY.glob("NBA_Products*.csv"):
        match = re.fullmatch(r"NBA_Products(\d+)\.csv", path.name)
        if match and int(match.group(1)) > last_page:
            path.unlink()


def scrape(headless: bool = False) -> list[list[dict[str, str]]]:
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--window-size=1440,1000")
    if headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(60)
        return collect_pages(driver)
    finally:
        driver.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="在背景執行 Chrome")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        pages = scrape(args.headless)
    except (WebDriverException, RuntimeError) as error:
        raise SystemExit(f"抓取失敗，未覆蓋輸出檔：{error}") from None

    for page_number, rows in enumerate(pages, 1):
        write_page(page_number, rows)
        print(f"儲存頁面: {page_number}")
    remove_stale_outputs(len(pages))
    print(f"完成，共儲存 {len(pages)} 頁、{sum(map(len, pages))} 筆商品。")


if __name__ == "__main__":
    main()
