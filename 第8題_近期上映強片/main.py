"""第 8 題：抓取開眼電影網近期上映推薦，輸出 movies.csv。"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


URL = "https://www.atmovies.com.tw/movie/next/"
OUTPUT = Path(__file__).with_name("movies.csv")
FIELDS = ["名稱", "上映時間", "連結網址"]


def parse_movies(html: str | bytes) -> list[dict[str, str]]:
    """只解析推薦清單，避免混入導覽列、下拉選單或其他電影。"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("ul.filmListAllX > li")
    if not items:
        raise RuntimeError("找不到近期上映推薦清單，網站可能已改版。")

    movies: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        link = item.select_one(".filmtitle a[href]")
        runtime = item.select_one(".runtime")
        if link is None or runtime is None:
            raise RuntimeError("電影資料缺少名稱、連結或上映時間，停止輸出。")
        title = link.get_text(" ", strip=True)
        match = re.search(
            r"上映日期[：:]\s*(\d{4}/\d{1,2}/\d{1,2})",
            runtime.get_text(" ", strip=True),
        )
        if not title or match is None:
            raise RuntimeError(f"電影 {title!r} 的名稱或上映日期不完整，停止輸出。")
        release_date = datetime.strptime(match.group(1), "%Y/%m/%d").strftime("%Y/%m/%d")
        url = urljoin(URL, link["href"])
        if url in seen:
            continue
        seen.add(url)
        movies.append({"名稱": title, "上映時間": release_date, "連結網址": url})
    return movies


def scrape() -> list[dict[str, str]]:
    response = requests.get(URL, timeout=30)
    response.raise_for_status()
    return parse_movies(response.content)


def main() -> None:
    try:
        movies = scrape()
    except (requests.RequestException, RuntimeError, ValueError) as error:
        raise SystemExit(f"抓取失敗，未覆蓋 CSV：{error}") from None

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(movies)

    for movie in movies:
        print(f"{movie['名稱']} | {movie['上映時間']} | {movie['連結網址']}")
    print(f"完成：{len(movies)} 部電影，已儲存至 {OUTPUT}")


if __name__ == "__main__":
    main()
