"""第 1 題：抓取開眼電影網本週新片。"""

from __future__ import annotations

import csv
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag


URL = "https://www.atmovies.com.tw/movie/new/"
OUTPUT = Path(__file__).with_name("movies.csv")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; school-scraper/1.0)"}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_item(title_link: Tag) -> Tag:
    """往上找同時包含片長與上映日期的電影區塊。"""
    for parent in title_link.parents:
        if not isinstance(parent, Tag):
            continue
        text = clean(parent.get_text(" ", strip=True))
        if "片長" in text and "上映日期" in text:
            return parent
    return title_link.parent if isinstance(title_link.parent, Tag) else title_link


def movie_description(item: Tag, title: str) -> str:
    """從電影區塊中找出內容簡介；網站版面變更時仍保留合理的備援。"""
    candidates = item.select("p, .filmIntro, .filmintro, .movie_intro, .description")
    candidates = [clean(node.get_text(" ", strip=True)) for node in candidates]
    candidates = [
        text
        for text in candidates
        if len(text) >= 20
        and title not in text
        and "片長" not in text
        and "上映日期" not in text
    ]
    if candidates:
        return max(candidates, key=len)

    text = clean(item.get_text(" ", strip=True))
    text = re.sub(r"片長[：:]\s*\d+\s*分.*", "", text)
    return text.replace(title, "", 1).strip()


def scrape_detail(
    url: str, fallback_title: str, recent_only: bool = False
) -> dict[str, str] | None:
    """讀取電影詳細頁，作為目前新版列表頁沒有片長欄位時的備援。"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException:
        return None
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = clean(soup.get_text(" ", strip=True))

    duration_match = re.search(r"片長[：:]\s*(\d+)\s*分", text)
    date_match = re.search(r"上映日期[：:]\s*(\d{4}/\d{1,2}/\d{1,2})", text)
    if not duration_match or not date_match:
        return None

    release_date = date.fromisoformat(date_match.group(1).replace("/", "-"))
    today = date.today()
    if recent_only and not today - timedelta(days=14) <= release_date <= today + timedelta(days=45):
        return None

    description = ""
    if "劇情簡介" in text:
        description = text.split("劇情簡介", 1)[1]
        for marker in ("更多劇照", "相關新聞", "導演：", "BBS 討論區"):
            description = description.split(marker, 1)[0]
        description = description.strip()

    return {
        "標題": fallback_title,
        "內容": description,
        "片長": f"{duration_match.group(1)} 分",
        "網址": url,
    }


def scrape() -> list[dict[str, str]]:
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    movies: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    # 電影名稱連結目前位於 app2.atmovies.com.tw；用網址特徵而非固定 CSS class，
    # 讓程式對網站小幅改版比較有韌性。
    for link in soup.find_all("a", href=True):
        title = clean(link.get_text(" ", strip=True))
        href = urljoin(URL, link["href"])
        if not title or href in seen_urls:
            continue
        if not re.search(r"atmovies\.com\.tw/(?:.*/)?(?:film|movie)/", href):
            continue
        if len(title) < 2 or title in {"電影", "電影首頁", "本周新片"}:
            continue

        item = find_item(link)
        text = clean(item.get_text(" ", strip=True))
        duration_match = re.search(r"片長[：:]\s*(\d+)\s*分", text)
        if not duration_match:
            # 避免把導覽列或一般電影連結誤判成資料列。
            continue

        seen_urls.add(href)
        movies.append(
            {
                "標題": title,
                "內容": movie_description(item, title),
                "片長": f"{duration_match.group(1)} 分",
                "網址": href,
            }
        )

    if not movies:
        # 新版開眼頁面可能先只放電影連結，片長與劇情簡介放在詳細頁。
        # 這裡再讀取詳細頁，並用上映日期排除文章中的舊片推薦連結。
        candidates: list[tuple[str, str]] = []
        from_options = False
        for option in soup.select("option[value]"):
            href = urljoin(URL, option["value"])
            raw_title = clean(option.get_text(" ", strip=True))
            title = raw_title.lstrip("★ ").strip()
            # 目前頁面的本週新片選項有 ★ 標記；遇到新版頁面沒有標記時，
            # 才退回使用文章中的 /film/ 連結。
            if raw_title.startswith("★") and title and re.search(r"/movie/f[a-z0-9]+/?$", href):
                candidates.append((href, title))
                from_options = True

        if not candidates:
            for link in soup.find_all("a", href=True):
                title = clean(link.get_text(" ", strip=True))
                href = urljoin(URL, link["href"])
                if title and "/film/" in href:
                    candidates.append((href, title))

        for href, title in candidates:
            if href in seen_urls:
                continue
            record = scrape_detail(href, title, recent_only=not from_options)
            if record:
                seen_urls.add(href)
                movies.append(record)

    if not movies:
        raise RuntimeError("找不到電影資料，可能是網站版面已變更。")
    return movies


def main() -> None:
    movies = scrape()
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=["標題", "內容", "片長", "網址"])
        writer.writeheader()
        writer.writerows(movies)
    print(f"完成：{len(movies)} 部電影，已儲存至 {OUTPUT.name}")


if __name__ == "__main__":
    main()
