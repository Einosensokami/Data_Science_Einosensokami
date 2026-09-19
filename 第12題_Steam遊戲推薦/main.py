"""第 12 題：使用 Selenium 搜尋 Google「Steam 遊戲推薦」並輸出 CSV。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
import truststore
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://www.google.com/?hl=zh-TW"
KEYWORD = "Steam 遊戲推薦"
OUTPUT = Path(__file__).with_name("steam_games.csv")
FIELDS = ["標題", "網址"]
RESULT_SELECTOR = "#search a h3"
GOOGLE_HOSTS = {"google.com", "www.google.com", "google.com.tw", "www.google.com.tw"}


def verification_required(driver: webdriver.Chrome) -> bool:
    return urlsplit(driver.current_url).path.startswith("/sorry/") or bool(
        driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha"], #captcha-form')
    )


def accept_consent_if_present(driver: webdriver.Chrome) -> None:
    """部分地區會先顯示 Cookie 選項；拒絕非必要 Cookie 後繼續。"""
    buttons = driver.find_elements(
        By.XPATH,
        "//button[.//*[normalize-space(.)='全部拒絕' or normalize-space(.)='拒絕全部' "
        "or normalize-space(.)='Reject all']]",
    )
    for button in buttons:
        if button.is_displayed() and button.is_enabled():
            button.click()
            return


def wait_for_results(driver: webdriver.Chrome, headless: bool) -> None:
    wait = WebDriverWait(driver, 30)
    wait.until(
        lambda browser: verification_required(browser)
        or browser.find_elements(By.CSS_SELECTOR, RESULT_SELECTOR)
    )
    if verification_required(driver):
        if headless:
            raise RuntimeError("Google 要求真人驗證，請移除 --headless 後執行，並在 Chrome 完成驗證。")
        print("Google 要求真人驗證，請在 Chrome 視窗中完成；程式最多等待 5 分鐘。", flush=True)
        try:
            WebDriverWait(driver, 300).until(
                lambda browser: not verification_required(browser)
                and browser.find_elements(By.CSS_SELECTOR, RESULT_SELECTOR)
            )
        except TimeoutException:
            raise RuntimeError("等待真人驗證逾時，尚未取得搜尋結果。") from None


def result_url(href: str) -> str:
    """若 Google 使用 /url 轉址，取出真正的目標網址。"""
    parsed = urlsplit(href)
    if parsed.hostname in GOOGLE_HOSTS and parsed.path == "/url":
        params = parse_qs(parsed.query)
        href = (params.get("q") or params.get("url") or [""])[0]
        parsed = urlsplit(href)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if parsed.hostname in GOOGLE_HOSTS and parsed.path in {"/search", "/imgres", "/url"}:
        return ""
    return href


def resolve_redirects(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Google /goto 使用不透明代碼，讀取其 HTTP Location 取得目標網址。"""
    truststore.inject_into_ssl()
    resolved = []
    seen = set()
    with requests.Session() as session:
        for row in rows:
            url = row["網址"]
            parsed = urlsplit(url)
            if parsed.hostname in GOOGLE_HOSTS and parsed.path == "/goto":
                # 搜尋與擷取仍由 Selenium 完成；只讀取轉址，不下載目標網站。
                response = session.get(url, timeout=20, allow_redirects=False)
                response.raise_for_status()
                location = response.headers.get("Location", "")
                url = result_url(urljoin(url, location)) if location else ""
                if not response.is_redirect or not url or urlsplit(url).hostname in GOOGLE_HOSTS:
                    raise RuntimeError("無法解析 Google 轉址，尚未取得可直接開啟的目標網址。")
            if url not in seen:
                seen.add(url)
                resolved.append({"標題": row["標題"], "網址": url})
    return resolved


def collect_results(driver: webdriver.Chrome) -> list[dict[str, str]]:
    """讀取第一頁搜尋區內的結果標題與連結，依網址去重。"""
    rows = []
    seen = set()
    for heading in driver.find_elements(By.CSS_SELECTOR, RESULT_SELECTOR):
        if not heading.is_displayed():
            continue
        title = " ".join(heading.text.split())
        link = heading.find_element(By.XPATH, "./ancestor::a[1]")
        url = result_url(link.get_attribute("href") or "")
        if not title or not url or url in seen:
            continue
        seen.add(url)
        rows.append({"標題": title, "網址": url})
    if not rows:
        raise RuntimeError("找不到有效的搜尋結果；Google 可能需要驗證或已變更頁面結構。")
    return rows


def scrape(headless: bool = False) -> list[dict[str, str]]:
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--window-size=1440,1000")
    options.page_load_strategy = "eager"
    if headless:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(60)
        driver.get(URL)
        accept_consent_if_present(driver)
        search = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.NAME, "q")))
        search.clear()
        search.send_keys(KEYWORD, Keys.ENTER)
        wait_for_results(driver, headless)
        return resolve_redirects(collect_results(driver))
    finally:
        driver.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="在背景執行 Chrome；遇真人驗證時停止")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        rows = scrape(args.headless)
    except (WebDriverException, requests.RequestException, RuntimeError) as error:
        raise SystemExit(f"抓取失敗，未覆蓋輸出檔：{error}") from None

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"搜尋關鍵字：{KEYWORD}\n")
    for number, row in enumerate(rows, 1):
        print(f"{number}. {row['標題']}\n{row['網址']}\n")
    print(f"已儲存 {len(rows)} 筆搜尋結果至 {OUTPUT}")


if __name__ == "__main__":
    main()
