"""第 6 題：抓取 CLE、HOU、GSW 的 2023–24 球季球員資料。"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Comment


TEAMS = ("CLE", "HOU", "GSW")
URL_TEMPLATE = "https://www.basketball-reference.com/teams/{team}/2024.html"
OUTPUT = Path(__file__).with_name("players.csv")
COLUMNS = {
    "背號": "number",
    "姓名": "player",
    "位置": "pos",
    "體重": "weight",
    "生日": "birth_date",
    "經驗": "years_experience",
    "大學": "college",
}
FIELDS = ["球隊", *COLUMNS]


def parse_roster(html: str | bytes, team: str) -> list[dict[str, str]]:
    """依 data-stat 解析 Roster，避免身高與出生國等額外欄位造成錯位。"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table#roster")
    # Basketball Reference 的部分表格可能包在 HTML 註解中。
    if table is None:
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            if "roster" not in comment:
                continue
            table = BeautifulSoup(str(comment), "html.parser").select_one("table#roster")
            if table is not None:
                break
    if table is None:
        raise RuntimeError(f"{team}：找不到 Roster 表格，網站可能拒絕連線或版面已變更。")

    rows: list[dict[str, str]] = []
    for tr in table.select("tbody tr"):
        if tr.select_one('[data-stat="player"] a[href^="/players/"]') is None:
            continue
        row = {"球隊": team}
        for label, stat in COLUMNS.items():
            cell = tr.select_one(f'[data-stat="{stat}"]')
            if cell is None:
                raise RuntimeError(f"{team}：球員資料缺少「{label}」欄位，停止輸出。")
            # 保留空白大學、R（新人）及 00 等背號，不轉成數值。
            row[label] = " ".join(cell.get_text().split())
        if not row["姓名"]:
            raise RuntimeError(f"{team}：球員姓名為空白，停止輸出。")
        rows.append(row)

    if not rows:
        raise RuntimeError(f"{team}：Roster 表格沒有球員資料。")
    return rows


def scrape() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with requests.Session() as session:
        for index, team in enumerate(TEAMS):
            if index:
                time.sleep(3)
            url = URL_TEMPLATE.format(team=team)
            print(f"正在抓取 {team}：{url}", flush=True)
            response = session.get(url, timeout=30)
            response.raise_for_status()
            team_rows = parse_roster(response.content, team)
            rows.extend(team_rows)
            print(f"{team}：取得 {len(team_rows)} 位球員", flush=True)
    return rows


def main() -> None:
    try:
        rows = scrape()
    except (requests.RequestException, RuntimeError) as error:
        raise SystemExit(f"抓取失敗，未覆蓋 CSV：{error}") from None

    # 三隊皆成功後才寫檔；UTF-8 BOM 可供 Excel 正確顯示中文。
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"已將 {len(rows)} 筆球員資料存入 {OUTPUT.name}")


if __name__ == "__main__":
    main()
