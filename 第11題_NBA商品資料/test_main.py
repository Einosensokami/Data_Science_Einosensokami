"""第 11 題 NBA 商品爬蟲的單元測試。"""

from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("main.py")
SPEC = importlib.util.spec_from_file_location("question11_main", MODULE_PATH)
assert SPEC and SPEC.loader
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)


class ParseProductsTests(unittest.TestCase):
    def test_parses_products_and_normalizes_whitespace(self) -> None:
        html = """
        <table id="our-table"><tbody id="table-body">
          <tr><td>1</td><td>  NBA   球衣 </td><td>1,190</td></tr>
          <tr><td>2</td><td>球帽</td><td>790</td></tr>
        </tbody></table>
        """

        self.assertEqual(
            main.parse_products(html),
            [
                {"商品編號": "1", "商品名稱": "NBA 球衣", "價格": "1,190"},
                {"商品編號": "2", "商品名稱": "球帽", "價格": "790"},
            ],
        )

    def test_rejects_missing_table(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "找不到 NBA 商品表格"):
            main.parse_products("<html></html>")

    def test_rejects_empty_table(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "沒有 NBA 商品資料"):
            main.parse_products('<table id="our-table"><tbody></tbody></table>')

    def test_rejects_wrong_cell_count(self) -> None:
        html = '<table id="our-table"><tbody><tr><td>1</td><td>球衣</td></tr></tbody></table>'
        with self.assertRaisesRegex(RuntimeError, "預期有 3 個欄位"):
            main.parse_products(html)

    def test_rejects_blank_required_field(self) -> None:
        html = (
            '<table id="our-table"><tbody>'
            '<tr><td>1</td><td> </td><td>990</td></tr>'
            '</tbody></table>'
        )
        with self.assertRaisesRegex(RuntimeError, "空白的必要欄位"):
            main.parse_products(html)


class CsvOutputTests(unittest.TestCase):
    def test_output_name_and_utf8_bom_round_trip(self) -> None:
        rows = [{"商品編號": "1", "商品名稱": "勇士隊球衣", "價格": "1,190"}]
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            with patch.object(main, "DIRECTORY", directory):
                self.assertEqual(main.output_path(3).name, "NBA_Products3.csv")
                path = main.write_page(3, rows)

            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            with path.open(newline="", encoding="utf-8-sig") as file:
                self.assertEqual(list(csv.DictReader(file)), rows)

    def test_removes_only_outputs_after_last_page(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            for page in range(1, 5):
                (directory / f"NBA_Products{page}.csv").touch()
            (directory / "NBA_Products-not-a-page.csv").touch()

            with patch.object(main, "DIRECTORY", directory):
                main.remove_stale_outputs(2)

            self.assertTrue((directory / "NBA_Products1.csv").exists())
            self.assertTrue((directory / "NBA_Products2.csv").exists())
            self.assertFalse((directory / "NBA_Products3.csv").exists())
            self.assertFalse((directory / "NBA_Products4.csv").exists())
            self.assertTrue((directory / "NBA_Products-not-a-page.csv").exists())


if __name__ == "__main__":
    unittest.main()
