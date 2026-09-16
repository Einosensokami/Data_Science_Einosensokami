"""第 2 題：抓取臺灣銀行牌告匯率並存成 bank.csv。"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag


URL = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
OUTPUT = Path(__file__).with_name("bank.csv")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; school-scraper/1.0)"}
NUMBER = re.compile(r"^(?:-|\d+(?:\.\d+)?)$")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def scrape() -> list[dict[str, str]]:
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    target_table: Tag | None = None
    for table in soup.find_all("table"):
        table_text = clean(table.get_text(" ", strip=True))
        if "美金" in table_text and "即期匯率" in table_text:
            target_table = table
            break
    if target_table is None:
        raise RuntimeError("找不到牌告匯率表，可能是網站版面已變更。")

    rows: list[dict[str, str]] = []
    for tr in target_table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        cell_texts = [clean(cell.get_text(" ", strip=True)) for cell in cells]
        row_text = " ".join(cell_texts)
        code_match = re.search(r"\(([A-Z]{3})\)", row_text)
        if not code_match:
            continue

        # 同一表格在桌面版與行動版可能重複顯示欄位；只取前四個數值，
        # 對應現金買入、現金賣出、即期買入、即期賣出。
        values = [text for text in cell_texts if NUMBER.fullmatch(text)]
        if len(values) < 4:
            continue

        currency = row_text[: row_text.find("(")].strip()
        rows.append(
            {
                "幣別代碼": code_match.group(1),
                "幣別": currency,
                "現金買入": values[0],
                "現金賣出": values[1],
                "即期買入": values[2],
                "即期賣出": values[3],
            }
        )
    if not rows:
        raise RuntimeError("牌告匯率表沒有可用資料。")
    return rows


def main() -> None:
    rows = scrape()
    fields = ["幣別代碼", "幣別", "現金買入", "現金賣出", "即期買入", "即期賣出"]
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"完成：{len(rows)} 種幣別，已儲存至 {OUTPUT.name}")


if __name__ == "__main__":
    main()
