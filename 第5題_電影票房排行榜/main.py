"""第 5 題：以 Selenium 操作開眼電影網，抓取台北週末票房排行榜。"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


START_URL = "https://www.atmovies.com.tw/movie/new/"
OUTPUT = Path(__file__).with_name("Taipei_movies.csv")
WAIT_SECONDS = 20
FIELDS = ["排名", "片名", "本週票房", "累計票房"]


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_taipei_ranking(html: str) -> list[dict[str, str]]:
    """解析台北週末票房的完整表格；每部電影由標題列與票房列組成。"""
    soup = BeautifulSoup(html, "html.parser")
    title = next(
        (heading for heading in soup.find_all("h3") if "台北週末票房排行榜" in heading.get_text()),
        None,
    )
    if title is None:
        raise RuntimeError("找不到台北週末票房排行榜。")

    summary_table = title.find_next("table")
    ranking_table = summary_table.find_next("table") if summary_table else None
    if ranking_table is None:
        raise RuntimeError("找不到台北票房表格。")

    rows: list[dict[str, str]] = []
    for title_row in ranking_table.find_all("tr"):
        rank = title_row.select_one("td > b")
        movie_link = title_row.select_one("td > a[href^='/film/']")
        if rank is None or movie_link is None:
            continue

        # 原始 HTML 的 <tr> 未完整關閉，BeautifulSoup 會將後續列巢狀化；
        # 因此以文件順序取得下一個 <tr>，不能使用 find_next_sibling。
        stats_row = title_row.find_next("tr")
        if stats_row is None:
            continue
        cells = stats_row.find_all("td", recursive=False)
        if len(cells) < 4:
            continue

        rows.append(
            {
                "排名": clean(rank.get_text()),
                "片名": clean(movie_link.get_text(" ", strip=True)),
                "本週票房": clean(cells[2].get_text()),
                "累計票房": clean(cells[3].get_text()),
            }
        )

    if len(rows) != 20:
        raise RuntimeError(f"預期取得 20 筆台北票房資料，實際取得 {len(rows)} 筆。")
    return rows


def open_taipei_ranking(driver: webdriver.Chrome) -> None:
    """以滑鼠移動與點選進入票房排行榜，並按下台北榜的 more。"""
    wait = WebDriverWait(driver, WAIT_SECONDS)
    driver.get(START_URL)

    # 「票房排行榜」位於「電影」的下拉選單，先以滑鼠移入展開選單。
    movie_menu = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "#dropdownMenu .menuTitle.arrow"))
    )
    ActionChains(driver).move_to_element(movie_menu).perform()
    box_office = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(@href, 'app2.atmovies.com.tw/boxoffice')]")
        )
    )
    ActionChains(driver).move_to_element(box_office).click().perform()
    wait.until(EC.url_contains("/boxoffice/"))

    taipei_more = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//h3[contains(., '台北週末票房排行榜')]"
                "/following::a[contains(concat(' ', normalize-space(@class), ' '), ' viewMore ')][1]",
            )
        )
    )
    ActionChains(driver).move_to_element(taipei_more).click().perform()
    wait.until(EC.url_contains("/boxoffice/twweekend/"))
    wait.until(EC.presence_of_element_located((By.XPATH, "//h3[contains(., '台北週末票房排行榜')]")))


def main() -> None:
    options = Options()
    # 網頁的第三方廣告可能長時間載入；主要文件完成後即可操作排行榜連結。
    options.page_load_strategy = "eager"
    options.add_argument("--lang=zh-TW")
    options.add_argument("--window-size=1440,1000")
    driver = webdriver.Chrome(options=options)

    try:
        open_taipei_ranking(driver)
        rows = parse_taipei_ranking(driver.page_source)
    finally:
        driver.quit()

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"已將 {len(rows)} 筆台北週末票房資料存入 {OUTPUT.name}")


if __name__ == "__main__":
    main()
