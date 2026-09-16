"""第 3 題：下載政府資料開放平臺的腸病毒 CSV。"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import requests


URL = "https://od.cdc.gov.tw/eic/NHI_EnteroviralInfection.csv"
OUTPUT = Path(__file__).with_name("NHI_EnteroviralInfection.csv")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; school-scraper/1.0)"}


def download() -> int:
    response = requests.get(URL, headers=HEADERS, timeout=60)
    response.raise_for_status()
    if not response.content.strip():
        raise RuntimeError("官方資料回傳空檔案。")

    # 原始 CSV 直接保存，避免改變官方資料內容；另外讀取一次確認確實是 CSV。
    text = response.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        raise RuntimeError("下載內容不像有效的 CSV 資料。")
    OUTPUT.write_bytes(response.content)
    return len(rows) - 1


def main() -> None:
    count = download()
    print(f"完成：{count} 筆資料，已儲存至 {OUTPUT.name}")


if __name__ == "__main__":
    main()
