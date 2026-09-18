"""第 9 題：使用 Selenium 擷取 Google 新聞首頁各分類的新聞標題。"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://news.google.com/home?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
DIRECTORY = Path(__file__).resolve().parent
GROUPS = ("焦點新聞", "地方新聞", "您的主題", "更多新聞")
LINKS = 'a[href*="/read/"], a[href*="/articles/"]'


def scroll_to_end(driver: webdriver.Chrome) -> None:
    """等候捲動後的延遲載入；連續三次高度與連結數不變才結束。"""
    previous = None
    stable = 0
    for _ in range(60):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        state = (
            driver.execute_script("return document.body.scrollHeight"),
            len(driver.find_elements(By.CSS_SELECTOR, LINKS)),
        )
        stable = stable + 1 if state == previous else 0
        if stable >= 3:
            return
        previous = state
    raise RuntimeError("捲動 60 次後頁面仍在載入，無法確認已取得本頁全部資料。")


def collect_group(driver: webdriver.Chrome, name: str) -> list[dict[str, str]]:
    headings = driver.find_elements(
        By.XPATH,
        f"//*[self::h1 or self::h2 or self::h3 or self::h4]"
        f"[normalize-space(.)='{name}']",
    )
    if not headings:
        return []
    heading = headings[0]
    # 主題及更多新聞各自是一個 section；焦點、地方則位於焦點提要內。
    if name in ("您的主題", "更多新聞"):
        containers = heading.find_elements(By.XPATH, "./ancestor::section[1]")
        if not containers:
            raise RuntimeError(f"{name} 的區塊結構已變更。")
        container = containers[0]
    else:
        container = heading
        while not container.find_elements(By.CSS_SELECTOR, LINKS):
            container = container.find_element(By.XPATH, "..")
            if container.tag_name in ("section", "body", "html"):
                # 不往外擷取其他分類，避免把整頁誤當地方新聞。
                return []
    rows = []
    seen = set()
    for link in container.find_elements(By.CSS_SELECTOR, LINKS):
        title = " ".join((link.get_attribute("textContent") or "").split())
        url = link.get_attribute("href")
        if not title or not url or url in seen:
            continue  # 排除沒有標題文字的圖片連結，分類內依網址去重。
        seen.add(url)
        rows.append({"分類": name, "標題": title, "網址": url})
    return rows


def scrape(headless: bool = False) -> tuple[str, dict[str, list[dict[str, str]]]]:
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--window-size=1440,1000")
    if headless:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(60)
        driver.get(URL)
        WebDriverWait(driver, 30).until(
            lambda browser: any(
                link.get_attribute("textContent").strip()
                for link in browser.find_elements(By.CSS_SELECTOR, LINKS)
            )
        )
        scroll_to_end(driver)
        groups = {name: collect_group(driver, name) for name in GROUPS}
        if not any(groups.values()):
            raise RuntimeError("找不到指定分類的新聞；網站可能已改版或需要互動驗證。")
        return driver.title, groups
    finally:
        driver.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="在背景執行 Chrome")
    args = parser.parse_args()
    # Windows 主控台的預設編碼可能無法列印新聞中的罕見字。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        title, groups = scrape(args.headless)
    except (WebDriverException, RuntimeError) as error:
        raise SystemExit(f"抓取失敗，未覆蓋輸出檔：{error}") from None

    lines = [f"網頁標題：{title}", f"來源：{URL}", "", "焦點提要：焦點新聞、地方新聞"]
    rows = []
    for name, news in groups.items():
        lines.extend(["", f"【{name}】共 {len(news)} 則"])
        if not news:
            lines.append("未取得新聞：此區塊可能未顯示、尚未設定地區／個人化，或頁面結構已變更。")
        for number, item in enumerate(news, 1):
            lines.append(f"{number}. {item['標題']}")
        rows.extend(news)
    report = "\n".join(lines) + "\n"
    with (DIRECTORY / "google_news.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=["分類", "標題", "網址"])
        writer.writeheader()
        writer.writerows(rows)
    (DIRECTORY / "google_news.txt").write_text(report, encoding="utf-8-sig")
    print(report)
    missing = [name for name, news in groups.items() if not news]
    if missing:
        print(f"部分完成：{'、'.join(missing)} 未取得新聞，請查看文字檔中的說明。")
    print(f"已儲存 {len(rows)} 則新聞至 {DIRECTORY / 'google_news.csv'}")


if __name__ == "__main__":
    main()
