"""第 14 題：擷取 HoopsHype 球員薪資表與前三名球員的背號。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://hoopshype.com/salaries/players/"
DIRECTORY = Path(__file__).resolve().parent
TABLE_XPATH = "//table[.//th[normalize-space()='Player'] and .//tbody/tr[1]/td[2]]"
PAGER_XPATH = "//table[.//th[normalize-space()='Player']]/../../following-sibling::div[1]"
PAGER_PATTERN = re.compile(r"^(\d+)\s+of\s+(\d+)$")
NUMBER_PATTERN = re.compile(r"^#\d+$")
HIGHEST_FIELDS = ["名字", "背號", "薪資"]


def clean(value: str) -> str:
    return re.sub(r"\$\s+", "$", " ".join(value.split()))


def parse_table(html: str) -> tuple[list[str], list[dict[str, str]], list[str]]:
    """解析目前顯示的薪資表，保留排名及每個球季的薪資欄位。"""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.select("table"):
        headings = [clean(th.get_text(" ", strip=True)) for th in table.select("thead th")]
        if len(headings) < 3 or headings[1] != "Player":
            continue
        fields = ["排名", "球員", *headings[2:]]
        rows: list[dict[str, str]] = []
        profile_urls: list[str] = []
        for index, tr in enumerate(table.select("tbody tr"), 1):
            cells = tr.select("td")
            if len(cells) != len(fields):
                raise RuntimeError(f"表格第 {index} 列的欄位數不符。")
            link = cells[1].select_one("a[href]")
            profile_url = urljoin(URL, link["href"]) if link else ""
            if profile_url and urlsplit(profile_url).hostname not in {"hoopshype.com", "www.hoopshype.com"}:
                raise RuntimeError(f"表格第 {index} 列的球員連結不屬於 HoopsHype。")
            values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
            if link:
                values[1] = clean(link.get_text(" ", strip=True))
            if any(not value for value in values):
                raise RuntimeError(f"表格第 {index} 列有空白欄位。")
            rows.append(dict(zip(fields, values)))
            profile_urls.append(profile_url)
        if not rows:
            raise RuntimeError("薪資表沒有球員資料。")
        return fields, rows, profile_urls
    raise RuntimeError("找不到 HoopsHype 球員薪資表。")


def pager_state_if_ready(driver: webdriver.Chrome) -> tuple[int, int] | None:
    pagers = driver.find_elements(By.XPATH, PAGER_XPATH)
    if len(pagers) != 1:
        return None
    match = PAGER_PATTERN.fullmatch(clean(pagers[0].get_attribute("textContent") or ""))
    if match is None:
        return None
    return int(match[1]), int(match[2])


def pager_state(driver: webdriver.Chrome) -> tuple[int, int]:
    state = pager_state_if_ready(driver)
    if state is None:
        raise RuntimeError("無法辨識薪資表頁碼。")
    return state


def first_row_signature(driver: webdriver.Chrome) -> str:
    return clean(driver.find_element(By.XPATH, TABLE_XPATH + "//tbody/tr[1]").text)


def page_loaded(driver: webdriver.Chrome, expected_page: int, previous_row: str) -> bool:
    """React 換頁時表格與分頁列會暫時消失，等待兩者一起更新。"""
    state = pager_state_if_ready(driver)
    if state is None or state[0] != expected_page:
        return False
    rows = driver.find_elements(By.XPATH, TABLE_XPATH + "//tbody/tr[1]")
    return bool(rows) and clean(rows[0].text) != previous_row


def collect_table(driver: webdriver.Chrome) -> tuple[list[str], list[dict[str, str]], list[tuple[str, str, str]], int]:
    wait = WebDriverWait(driver, 30, ignored_exceptions=(StaleElementReferenceException,))
    driver.get(URL)
    wait.until(EC.presence_of_element_located((By.XPATH, TABLE_XPATH)))
    wait.until(lambda browser: pager_state_if_ready(browser) is not None)

    all_rows: list[dict[str, str]] = []
    top_three: list[tuple[str, str, str]] = []
    fields: list[str] | None = None
    page = 1
    total_pages = 0

    while True:
        current_page, reported_total = pager_state(driver)
        if current_page != page or (total_pages and reported_total != total_pages):
            raise RuntimeError("薪資表頁碼未依序更新。")
        total_pages = reported_total
        try:
            current_fields, rows, urls = parse_table(driver.page_source)
        except RuntimeError as error:
            raise RuntimeError(f"第 {page} 頁：{error}") from error
        if fields is None:
            fields = current_fields
        elif current_fields != fields:
            raise RuntimeError("薪資表跨頁欄位不一致。")
        for row, profile_url in zip(rows, urls):
            all_rows.append(row)
            if len(top_three) < 3:
                if not profile_url:
                    raise RuntimeError(f"薪資前三名 {row['球員']} 沒有個人頁連結，無法讀取背號。")
                top_three.append((row["球員"], row[fields[2]], profile_url))
        print(f"已擷取薪資表第 {page}/{total_pages} 頁，累計 {len(all_rows)} 列。", flush=True)
        if page == total_pages:
            break

        buttons = driver.find_elements(By.XPATH, PAGER_XPATH + "//button")
        if len(buttons) != 2 or not buttons[1].is_enabled():
            raise RuntimeError(f"薪資表第 {page} 頁無法前往下一頁。")
        previous_row = first_row_signature(driver)
        driver.execute_script("arguments[0].click();", buttons[1])
        page += 1
        try:
            wait.until(lambda browser: page_loaded(browser, page, previous_row))
        except TimeoutException:
            raise RuntimeError(f"從第 {page - 1} 頁切換到第 {page} 頁逾時。") from None

    if fields is None or len(top_three) != 3:
        raise RuntimeError("薪資表不足三位球員。")
    return fields, all_rows, top_three, total_pages


def parse_profile_number(html: str, profile_url: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    headings = soup.select("h2")
    if len(headings) != 1:
        raise RuntimeError(f"球員頁面找不到唯一的姓名：{profile_url}")
    heading = headings[0]
    name = clean(heading.get_text(" ", strip=True))
    number = heading.parent.find(string=lambda value: bool(value and NUMBER_PATTERN.fullmatch(value.strip())))
    if not name or number is None:
        raise RuntimeError(f"球員頁面找不到姓名或背號：{profile_url}")
    return name, number.strip().lstrip("#")


def scrape(headless: bool = False) -> tuple[list[str], list[dict[str, str]], list[dict[str, str]], int]:
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--window-size=1440,1000")
    options.page_load_strategy = "eager"
    if headless:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(60)
        fields, all_rows, top_three, pages = collect_table(driver)
        highest: list[dict[str, str]] = []
        for table_name, salary, profile_url in top_three:
            driver.get(profile_url)
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//h2/..//span[starts-with(normalize-space(.), '#')]")
                    )
                )
            except TimeoutException:
                raise RuntimeError(f"等待球員 {table_name} 的背號逾時。") from None
            name, number = parse_profile_number(driver.page_source, profile_url)
            highest.append({"名字": name, "背號": number, "薪資": salary})
        return fields, all_rows, highest, pages
    except TimeoutException:
        raise RuntimeError("等待 HoopsHype 表格、分頁或球員資料逾時。") from None
    finally:
        driver.quit()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="在背景執行 Chrome")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        fields, all_rows, highest, pages = scrape(args.headless)
    except (WebDriverException, RuntimeError) as error:
        raise SystemExit(f"抓取失敗，未覆蓋輸出檔：{error}") from None

    write_csv(DIRECTORY / "highest.csv", HIGHEST_FIELDS, highest)
    write_csv(DIRECTORY / "all_play.csv", fields, all_rows)
    print(f"球季：{fields[2]}；完成 {pages} 頁、{len(all_rows)} 筆薪資資料。")
    for row in highest:
        print(f"{row['名字']} #{row['背號']}：{row['薪資']}")
    print(f"已儲存 {DIRECTORY / 'highest.csv'} 與 {DIRECTORY / 'all_play.csv'}")


if __name__ == "__main__":
    main()
