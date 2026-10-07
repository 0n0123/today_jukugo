import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from scripts.generate_site import render_page, select_entry
from scripts.prepare_dictionary import collect_idioms, is_kanji_word


class KanjiFilterTests(unittest.TestCase):
    def test_accepts_two_to_four_kanji(self):
        self.assertTrue(is_kanji_word("熟語"))
        self.assertTrue(is_kanji_word("人々"))
        self.assertTrue(is_kanji_word("四字熟語"))

    def test_rejects_other_lengths_and_scripts(self):
        self.assertFalse(is_kanji_word("語"))
        self.assertFalse(is_kanji_word("五文字熟語"))
        self.assertFalse(is_kanji_word("学習する"))


class DictionaryExtractionTests(unittest.TestCase):
    def test_filters_and_selects_one_sense_per_word(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.sqlite3"
            connection = sqlite3.connect(source_path)
            connection.executescript(
                """
                CREATE TABLE word (wordid INTEGER, lang TEXT, lemma TEXT, pos TEXT);
                CREATE TABLE sense (
                    wordid INTEGER, synset TEXT, lang TEXT, freq INTEGER, rank TEXT
                );
                CREATE TABLE synset_def (synset TEXT, lang TEXT, def TEXT, sid TEXT);
                CREATE TABLE synset_ex (synset TEXT, lang TEXT, def TEXT, sid TEXT);
                """
            )
            connection.executemany(
                "INSERT INTO word VALUES (?, 'jpn', ?, ?)",
                [
                    (1, "熟語", "n"),
                    (2, "熟語", "n"),
                    (3, "洗練", "v"),
                    (4, "学習する", "v"),
                    (5, "欠例", "n"),
                    (6, "素早く", "r"),
                ],
            )
            connection.executemany(
                "INSERT INTO sense VALUES (?, ?, 'jpn', ?, ?)",
                [
                    (1, "sense-low", 2, "1"),
                    (2, "sense-high", 9, "2"),
                    (3, "verb-sense", 1, "1"),
                    (4, "kana-sense", 1, "1"),
                    (5, "no-example", 1, "1"),
                    (6, "adverb-sense", 1, "1"),
                ],
            )
            connection.executemany(
                "INSERT INTO synset_def VALUES (?, 'jpn', ?, '0')",
                [
                    ("sense-low", "低頻度の意味"),
                    ("sense-high", "代表的な意味"),
                    ("verb-sense", "磨き上げる"),
                    ("kana-sense", "学ぶこと"),
                    ("no-example", "例文のない意味"),
                    ("adverb-sense", "速く"),
                ],
            )
            connection.executemany(
                "INSERT INTO synset_ex VALUES (?, 'jpn', ?, '0')",
                [
                    ("sense-low", "対象語を含まない例文"),
                    ("sense-low", "熟語を使った例文"),
                    ("sense-high", "別の言葉を使った例文"),
                    ("verb-sense", "技術を洗練する"),
                    ("kana-sense", "毎日学習する"),
                    ("adverb-sense", "素早く動く"),
                ],
            )
            connection.commit()
            connection.close()

            idioms = collect_idioms(source_path)

        by_word = {entry["word"]: entry for entry in idioms}
        self.assertEqual(set(by_word), {"熟語", "洗練"})
        self.assertEqual(by_word["熟語"]["meaning"], "低頻度の意味")
        self.assertEqual(by_word["熟語"]["example"], "熟語を使った例文")
        self.assertEqual(by_word["熟語"]["reading"], "じゅくご")
        self.assertEqual(by_word["洗練"]["display_word"], "洗練する")
        self.assertEqual(by_word["洗練"]["reading"], "せんれんする")
        self.assertEqual(by_word["洗練"]["part_of_speech"], "サ変動詞")


class DailySelectionTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {
                "word": f"熟語{index}",
                "display_word": f"熟語{index}",
                "reading": f"じゅくご{index}",
                "part_of_speech": "名詞",
                "synset": str(index),
                "meaning": "意味",
                "example": "用例",
            }
            for index in range(4)
        ]

    def test_daily_sequence_is_stable_and_cycles_without_early_repeats(self):
        start = date(2026, 10, 7)
        selected = [
            select_entry(self.entries, start + timedelta(days=offset))
            for offset in range(len(self.entries))
        ]

        self.assertEqual(len({entry["word"] for entry in selected}), len(self.entries))
        self.assertEqual(
            select_entry(self.entries, start)["word"],
            select_entry(self.entries, start)["word"],
        )
        self.assertEqual(
            select_entry(self.entries, start)["word"],
            select_entry(self.entries, start + timedelta(days=len(self.entries)))["word"],
        )

    def test_rendered_dictionary_text_is_escaped(self):
        entry = {**self.entries[0], "meaning": "<script>alert(1)</script>"}
        page = render_page(entry, date(2026, 10, 7))

        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("<title>今日の熟語</title>", page)
        self.assertIn("<rt>じゅくご0</rt>", page)


if __name__ == "__main__":
    unittest.main()