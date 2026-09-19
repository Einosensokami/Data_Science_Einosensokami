"""第 10 題：使用 Selenium 通過 PTT 分級確認，列出八卦板文章。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://www.ptt.cc/bbs/Gossiping/index.html"
DIRECTORY = Path(__file__).resolve().parent
ARTICLE_SELECTOR = ".r-list-container .r-ent"
AGE_BUTTON = 'button[name="yes"]'
FIELDS = ["網址", "標題", "作者"]


def collect_articles(driver: webdriver.Chrome) -> list[dict[str, str]]:
    """依頁面順序擷取文章（含置底公告），略過沒有連結的刪除文章。"""
    rows = []
    for entry in driver.find_elements(By.CSS_SELECTOR, ARTICLE_SELECTOR):
        links = entry.find_elements(By.CSS_SELECTOR, ".title a")
        if not links:
            continue
        link = links[0]
        # 取得瀏覽器解析後的完整網址，讓輸出可直接貼到 Chrome 開啟。
        url = link.get_attribute("href") or ""
        title = link.text.strip()
        authors = entry.find_elements(By.CSS_SELECTOR, ".meta .author")
        author = authors[0].text.strip() if authors else ""
        if not url.startswith("https://www.ptt.cc/bbs/Gossiping/") or not title or not author:
            raise RuntimeError("文章的網址、標題或作者缺漏，請確認網站結構。")
        rows.append({"網址": url, "標題": title, "作者": author})
    if not rows:
        raise RuntimeError("本頁沒有可擷取的文章連結。")
    return rows


def scrape(headless: bool = False) -> tuple[str, list[dict[str, str]]]:
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
        wait.until(
            lambda browser: browser.find_elements(By.CSS_SELECTOR, AGE_BUTTON)
            or browser.find_elements(By.CSS_SELECTOR, ARTICLE_SELECTOR)
        )
        if driver.find_elements(By.CSS_SELECTOR, AGE_BUTTON):
            # 實際點選成年確認，讓網站設定 over18=1 Cookie 並返回文章列表。
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, AGE_BUTTON))).click()
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ARTICLE_SELECTOR)))
        cookie = driver.get_cookie("over18")
        if not cookie or cookie["value"] != "1":
            raise RuntimeError("未取得 over18=1 Cookie，分級確認尚未完成。")
        title = driver.title.strip()
        if not title:
            raise RuntimeError("網頁 title 為空白。")
        return title, collect_articles(driver)
    finally:
        driver.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="在背景執行 Chrome")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        title, rows = scrape(args.headless)
    except (WebDriverException, RuntimeError) as error:
        raise SystemExit(f"抓取失敗，未覆蓋輸出檔：{error}") from None

    lines = [f"網頁標題：{title}", f"來源：{URL}", ""]
    for row in rows:
        lines.extend([row["網址"], row["標題"], row["作者"], ""])
    report = "\n".join(lines) + "\n"
    with (DIRECTORY / "gossiping.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (DIRECTORY / "gossiping.txt").write_text(report, encoding="utf-8-sig")
    print(report)
    print(f"已儲存 {len(rows)} 篇文章至 {DIRECTORY / 'gossiping.csv'}")


if __name__ == "__main__":
    main()
