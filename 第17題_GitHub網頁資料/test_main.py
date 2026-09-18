"""離線驗證題目紅框解析；測試資料不是實際 GitHub 擷取結果。"""

import tempfile
import unittest
from pathlib import Path

from main import FIELDS, parse_windows, save_csv


class WindowParsingTests(unittest.TestCase):
    def test_extracts_only_the_two_cards(self):
        html = """
        <aside><section><h2>Create your first project</h2>
          <p>Ready to start building? Create a repository.</p>
          <a href='/new'>Create repository</a></section><p>Recent activity</p></aside>
        <main><section><h3>Updates to your <span>homepage feed</span></h3>
          <p>First paragraph.</p><p>Second paragraph.</p></section>
          <section><h3>Start writing code</h3><p>Unrelated content</p></section></main>
        """
        rows = parse_windows(html, "https://github.com/")
        self.assertEqual([row["狀態"] for row in rows], ["已擷取", "已擷取"])
        self.assertEqual(rows[0]["內容"], "Ready to start building? Create a repository.")
        self.assertEqual(rows[1]["內容"], "First paragraph.\nSecond paragraph.")

    def test_missing_cards_do_not_capture_other_content(self):
        rows = parse_windows("<main><h1>Home</h1><p>Other feed</p></main>", "https://github.com/")
        self.assertTrue(all(row["狀態"] == "未顯示" and not row["內容"] for row in rows))

    def test_title_without_body_is_not_success(self):
        rows = parse_windows(
            "<aside><h2>Create your first project</h2></aside><main><p>Other content</p></main>",
            "https://github.com/",
        )
        self.assertEqual(rows[0]["狀態"], "找到標題但無法解析內容")
        self.assertEqual(rows[0]["內容"], "")

    def test_hidden_cards_are_not_reported(self):
        rows = parse_windows(
            "<div hidden><h2>Create your first project</h2><p>Hidden content</p></div>",
            "https://github.com/",
        )
        self.assertEqual(rows[0]["狀態"], "未顯示")

    def test_csv_preserves_unicode_and_multiline_text(self):
        import csv

        rows = parse_windows(
            "<section><h2>Create your first project</h2><p>測試,內容</p><p>下一段</p></section>",
            "https://github.com/",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.csv"
            save_csv(path, rows, FIELDS)
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            with path.open(encoding="utf-8-sig", newline="") as file:
                self.assertEqual(list(csv.DictReader(file)), rows)


if __name__ == "__main__":
    unittest.main()
