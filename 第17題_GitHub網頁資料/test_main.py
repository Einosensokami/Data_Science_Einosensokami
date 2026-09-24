"""離線驗證 GitHub 左欄 repository 與中欄 Feed 的解析。"""
import csv
import tempfile
import unittest
from pathlib import Path

from main import FIELDS, parse_dashboard, save_csv


class DashboardParsingTests(unittest.TestCase):
    def test_extracts_left_repositories_and_middle_feed(self):
        html = """
        <aside><h2>Top repositories</h2>
          <a href='/eino/project-a'>eino/project-a</a>
          <a href='/eino/project-b'>eino/project-b</a><a href='/eino'>Profile</a></aside>
        <main><section><h2>Feed</h2>
          <article><a href='/octo/repo/issues/1'>octo opened an issue</a><p>Useful details</p></article>
          <article><p>A second activity</p></article></section></main>
        """
        rows = parse_dashboard(html, "https://github.com/")
        repositories = [row for row in rows if row["區域"] == "左欄 repository"]
        feed = [row for row in rows if row["區域"] == "中欄 Feed"]
        self.assertEqual([row["項目"] for row in repositories], ["eino/project-a", "eino/project-b"])
        self.assertEqual(repositories[0]["連結"], "https://github.com/eino/project-a")
        self.assertEqual([row["內容"] for row in feed], ["octo opened an issue Useful details", "A second activity"])

    def test_missing_sections_are_reported_without_other_content(self):
        rows = parse_dashboard("<main><h1>Home</h1><p>Other content</p></main>", "https://github.com/")
        self.assertEqual([row["狀態"] for row in rows], ["未顯示", "未顯示"])

    def test_hidden_sections_are_not_reported(self):
        rows = parse_dashboard("<aside hidden><h2>Top repositories</h2><a href='/a/b'>a/b</a></aside>", "https://github.com/")
        self.assertEqual(rows[0]["狀態"], "未顯示")

    def test_csv_preserves_unicode(self):
        rows = parse_dashboard("<aside><h2>Top repositories</h2><a href='/測試/專案'>測試/專案</a></aside>", "https://github.com/")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.csv"
            save_csv(path, rows, FIELDS)
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            with path.open(encoding="utf-8-sig", newline="") as file:
                self.assertEqual(list(csv.DictReader(file)), rows)


if __name__ == "__main__":
    unittest.main()
