"""離線驗證 GitHub 左欄 repository 與中欄 Feed 的解析。"""
import csv
import tempfile
import unittest
from pathlib import Path

from main import FIELDS, login_complete, parse_dashboard, save_csv


class FakeBrowser:
    def __init__(self, *, url="https://github.com/login", meta_content="", logged_in=None):
        self.current_url = url
        self.meta_content = meta_content
        self.logged_in = logged_in

    def find_elements(self, by, selector):
        if selector == "meta[name='user-login']" and self.meta_content is not None:
            return [FakeElement(self.meta_content)]
        return []

    def get_cookie(self, name):
        if name == "logged_in" and self.logged_in is not None:
            return {"value": self.logged_in}
        return None


class FakeElement:
    def __init__(self, content):
        self.content = content

    def get_attribute(self, name):
        return self.content if name == "content" else None

    def is_displayed(self):
        return True

    @property
    def text(self):
        return ""


class DashboardParsingTests(unittest.TestCase):
    def test_login_cookie_completes_login_when_dashboard_lacks_meta_tag(self):
        """GitHub can omit meta[user-login] from a rendered dashboard."""
        browser = FakeBrowser(url="https://github.com/", meta_content=None, logged_in="yes")
        self.assertTrue(login_complete(browser))

    def test_logged_out_homepage_does_not_complete_login(self):
        browser = FakeBrowser(url="https://github.com/", meta_content=None, logged_in=None)
        self.assertFalse(login_complete(browser))

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
