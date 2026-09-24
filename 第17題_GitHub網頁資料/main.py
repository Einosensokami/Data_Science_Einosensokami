"""第 17 題：登入 GitHub 後擷取左欄 repository 與中欄 Feed。"""
from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

OUTPUT_DIR = Path(__file__).resolve().parent
WAIT_SECONDS, LOGIN_WAIT_SECONDS = 30, 300
FIELDS = ["區域", "項目", "內容", "連結", "頁面網址", "狀態"]
REPOSITORY_URL = re.compile(r"^/[^/]+/[^/]+/?$")


def clean(text: str) -> str:
    return " ".join(text.split())


def visible_soup(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for hidden in soup.select("script, style, template, [hidden], [aria-hidden='true']"):
        hidden.decompose()
    return soup


def find_heading(soup: BeautifulSoup, title: str) -> Tag | None:
    return soup.find(lambda tag: isinstance(tag, Tag) and tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"} and clean(tag.get_text(" ", strip=True)).casefold() == title.casefold())


def placeholder(area: str, page_url: str, status: str) -> dict[str, str]:
    return {"區域": area, "項目": "", "內容": "", "連結": "", "頁面網址": page_url, "狀態": status}


def repository_rows(soup: BeautifulSoup, page_url: str) -> list[dict[str, str]]:
    """擷取左欄 Top repositories 中每個 repository 的名稱與連結。"""
    heading = find_heading(soup, "Top repositories")
    if heading is None:
        return [placeholder("左欄 repository", page_url, "未顯示")]
    container = None
    for candidate in [heading, *heading.parents]:
        if not isinstance(candidate, Tag) or candidate.name in {"body", "html"}:
            break
        if candidate.find_all("a", href=REPOSITORY_URL):
            container = candidate
            break
    if container is None:
        return [placeholder("左欄 repository", page_url, "找到標題但無 repository")]
    rows, seen = [], set()
    for link in container.find_all("a", href=REPOSITORY_URL):
        href, name = link.get("href", ""), clean(link.get_text(" ", strip=True))
        if not name or href in seen:
            continue
        seen.add(href)
        rows.append({"區域": "左欄 repository", "項目": name, "內容": name, "連結": urljoin(page_url, href), "頁面網址": page_url, "狀態": "已擷取"})
    return rows or [placeholder("左欄 repository", page_url, "找到標題但無 repository")]


def feed_rows(soup: BeautifulSoup, page_url: str) -> list[dict[str, str]]:
    """擷取中欄 Feed 標題下的每一筆動態文字與第一個連結。"""
    heading = find_heading(soup, "Feed")
    if heading is None:
        return [placeholder("中欄 Feed", page_url, "未顯示")]
    section = None
    for candidate in [heading.parent, *(heading.parent.parents if heading.parent else [])]:
        if not isinstance(candidate, Tag) or candidate.name in {"body", "html", "main"}:
            break
        if candidate.find("article"):
            section = candidate
            break
    section = section or (heading.parent if isinstance(heading.parent, Tag) else None)
    entries = section.find_all("article") if section else []
    if not entries and section:
        entries = [child for child in section.find_all(recursive=False) if child is not heading and clean(child.get_text(" ", strip=True))]
    rows = []
    for index, entry in enumerate(entries, 1):
        text = clean(entry.get_text(" ", strip=True))
        if not text or text.casefold() == "feed":
            continue
        first_link = entry.find("a", href=True)
        rows.append({"區域": "中欄 Feed", "項目": f"Feed {index}", "內容": text, "連結": urljoin(page_url, first_link["href"]) if first_link else "", "頁面網址": page_url, "狀態": "已擷取"})
    return rows or [placeholder("中欄 Feed", page_url, "找到標題但無動態")]


def parse_dashboard(html: str, page_url: str) -> list[dict[str, str]]:
    soup = visible_soup(html)
    return [*repository_rows(soup, page_url), *feed_rows(soup, page_url)]


def login(driver: webdriver.Chrome, username: str, password: str) -> None:
    driver.get("https://github.com/login")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    wait.until(EC.visibility_of_element_located((By.ID, "login_field"))).send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='commit']"))).click()
    print("已送出登入資料；若需要二階段或裝置驗證，請在瀏覽器內完成（最多等待 5 分鐘）。")
    def logged_in(browser: webdriver.Chrome) -> bool:
        identity = browser.find_elements(By.CSS_SELECTOR, "meta[name='user-login']")
        if identity and identity[0].get_attribute("content"):
            return True
        for error in browser.find_elements(By.CSS_SELECTOR, ".flash-error"):
            if error.is_displayed() and error.text.strip():
                raise RuntimeError(f"GitHub 登入失敗：{error.text.strip()}")
        return False
    try:
        WebDriverWait(driver, LOGIN_WAIT_SECONDS).until(logged_in)
    except TimeoutException as exc:
        raise RuntimeError("登入逾時，請確認帳密或在瀏覽器中完成驗證。") from exc


def save_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def scrape_dashboard(driver: webdriver.Chrome) -> list[dict[str, str]]:
    driver.get("https://github.com/")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    wait.until(EC.visibility_of_element_located((By.TAG_NAME, "main")))
    wait.until(lambda browser: browser.execute_script("return document.readyState") == "complete")
    try:
        wait.until(lambda browser: any(row["狀態"] == "已擷取" for row in parse_dashboard(browser.page_source, browser.current_url)))
    except TimeoutException:
        pass
    rows = parse_dashboard(driver.page_source, driver.current_url)
    if not driver.save_screenshot(str(OUTPUT_DIR / "github_dashboard.png")):
        raise RuntimeError("無法儲存登入後首頁截圖。")
    return rows


def main() -> None:
    username = os.environ.get("GITHUB_USERNAME") or input("GitHub 帳號：").strip()
    password = os.environ.get("GITHUB_PASSWORD") or input("GitHub 密碼：")
    if not username or not password:
        raise RuntimeError("帳號與密碼不可空白。")
    options = Options()
    options.add_argument("--lang=en-US")
    options.add_argument("--window-size=1440,1000")
    driver = webdriver.Chrome(options=options)
    try:
        login(driver, username, password)
        rows = scrape_dashboard(driver)
    finally:
        driver.quit()
    output = OUTPUT_DIR / "github_dashboard.csv"
    save_csv(output, rows, FIELDS)
    for row in rows:
        print(f"[{row['區域']}] {row['項目']}：{row['內容']} ({row['狀態']})")
    print(f"\n已輸出 {output.name} 與 github_dashboard.png")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, TimeoutException) as exc:
        raise SystemExit(str(exc)) from None
    except (KeyboardInterrupt, EOFError):
        raise SystemExit("已取消執行。") from None
