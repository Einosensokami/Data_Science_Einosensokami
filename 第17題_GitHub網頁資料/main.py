"""第 17 題：使用 Selenium 登入 GitHub 並擷取題目指定資料。"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


OUTPUT_DIR = Path(__file__).resolve().parent
WAIT_SECONDS = 30
LOGIN_WAIT_SECONDS = 300
FIELDS = ["視窗", "標題", "內容", "頁面網址", "狀態"]
WINDOWS = [("1", "Create your first project"), ("2", "Updates to your homepage feed")]


def clean(text: str) -> str:
    return " ".join(text.split())


def parse_windows(html: str, page_url: str) -> list[dict[str, str]]:
    """依 PDF 紅框標題找對應段落；缺少舊版提示時保留明確狀態。"""
    soup = BeautifulSoup(html, "html.parser")
    for hidden in soup.select("script, style, template, [hidden], [aria-hidden='true']"):
        hidden.decompose()
    rows = []
    for number, title in WINDOWS:
        matches = soup.find_all(
            lambda tag: tag.name in {"h1", "h2", "h3", "h4", "h5", "h6", "a", "span", "strong", "div"}
            and clean(tag.get_text(" ", strip=True)) == title
        )
        paragraphs: list[str] = []
        for heading in matches:
            # 從最小容器往上找說明段落，不能把整個側欄或首頁當成紅框。
            for container in heading.parents:
                if not isinstance(container, Tag) or container.name in {"html", "body", "main", "aside"}:
                    break
                if container.find(["main", "aside"]) or len(container.get_text()) > 5000:
                    break
                paragraphs = [
                    clean(p.get_text(" ", strip=True))
                    for p in container.find_all("p")
                    if clean(p.get_text(" ", strip=True)) not in {"", title}
                ]
                if paragraphs:
                    break
            if paragraphs:
                break
        rows.append({
            "視窗": number,
            "標題": title,
            "內容": "\n".join(paragraphs),
            "頁面網址": page_url,
            "狀態": "已擷取" if paragraphs else ("找到標題但無法解析內容" if matches else "未顯示"),
        })
    return rows


def login(driver: webdriver.Chrome, username: str, password: str) -> None:
    """提交網站原始表單，隱藏的 authenticity_token 由瀏覽器一併送出。"""
    driver.get("https://github.com/login")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    wait.until(EC.visibility_of_element_located((By.ID, "login_field"))).send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='commit']"))).click()
    print("已提交登入表單；若出現二階段驗證或裝置驗證，請在瀏覽器完成（最多等待 5 分鐘）。")

    def logged_in(browser: webdriver.Chrome) -> bool:
        # 不能僅用網址判定：驗證頁也是登入流程中的其他網址。
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
        raise RuntimeError("登入或驗證逾時，尚未取得登入後資料。") from exc


def save_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def scrape_windows(driver: webdriver.Chrome) -> list[dict[str, str]]:
    driver.get("https://github.com/")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    wait.until(EC.visibility_of_element_located((By.TAG_NAME, "main")))
    wait.until(lambda browser: browser.execute_script("return document.readyState") == "complete")
    try:
        # 提示可能由 JavaScript 稍後載入；最多等待 30 秒，缺少時才記錄未顯示。
        wait.until(lambda browser: all(
            row["狀態"] == "已擷取" for row in parse_windows(browser.page_source, browser.current_url)
        ))
    except TimeoutException:
        pass
    rows = parse_windows(driver.page_source, driver.current_url)
    if not driver.save_screenshot(str(OUTPUT_DIR / "github_dashboard.png")):
        raise RuntimeError("無法儲存登入後的畫面截圖。")
    return rows


def main() -> None:
    username = os.environ.get("GITHUB_USERNAME") or input("GitHub 帳號或電子郵件：").strip()
    password = os.environ.get("GITHUB_PASSWORD") or input("GitHub 密碼（輸入時會顯示）：")
    if not username or not password:
        raise RuntimeError("帳號與密碼不可空白。")

    options = Options()
    options.add_argument("--lang=en-US")
    options.add_argument("--window-size=1440,1000")
    driver = webdriver.Chrome(options=options)
    try:
        login(driver, username, password)
        rows = scrape_windows(driver)
    finally:
        driver.quit()

    output = OUTPUT_DIR / "github_windows.csv"
    save_csv(output, rows, FIELDS)
    for row in rows:
        print(f"\n視窗 {row['視窗']}：{row['標題']}（{row['狀態']}）")
        if row["內容"]:
            print(row["內容"])
    print(f"\n已儲存 {output.name} 與 github_dashboard.png。")
    if any(row["狀態"] != "已擷取" for row in rows):
        print("未取得兩個紅框的完整內容；請核對截圖。舊版提示可能已移除，或此帳號不會顯示。")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, TimeoutException) as exc:
        raise SystemExit(str(exc)) from None
    except (KeyboardInterrupt, EOFError):
        raise SystemExit("已取消執行。") from None
