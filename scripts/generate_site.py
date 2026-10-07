import argparse
import html
import random
import sqlite3
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "idioms.sqlite3"
DEFAULT_OUTPUT = ROOT / "public" / "index.html"
START_DATE = date(2026, 10, 7)
TIME_ZONE = ZoneInfo("Asia/Tokyo")


def load_entries(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            """
            SELECT word, display_word, reading, part_of_speech, synset, meaning, example
            FROM idiom
            ORDER BY word
            """
        ).fetchall()
    finally:
        connection.close()


def select_entry(entries, target_date):
    if not entries:
        raise ValueError("The idiom database contains no entries.")

    ordered_entries = list(entries)
    random.Random("today-jukugo-v1").shuffle(ordered_entries)
    day_number = (target_date - START_DATE).days
    return ordered_entries[day_number % len(ordered_entries)]


def render_page(entry, target_date):
    display_word = html.escape(entry["display_word"])
    reading = html.escape(entry["reading"])
    part_of_speech = html.escape(entry["part_of_speech"])
    meaning = html.escape(entry["meaning"])
    example = html.escape(entry["example"])
    iso_date = target_date.isoformat()
    formatted_date = target_date.strftime("%Y年%m月%d日")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="毎日ひとつ、日本語の熟語を意味と用例から学びます。">
    <meta name="theme-color" content="#f5f6f2">
    <title>今日の熟語</title>
    <link rel="stylesheet" href="./style.css">
</head>
<body>
    <header class="site-header">
        <a class="site-name" href="./">今日の熟語</a>
        <p class="site-note">一日ひとつ、ことばを深く。</p>
    </header>

    <main>
        <article class="lesson" aria-labelledby="idiom-title">
            <div class="lesson-index">
                <span class="index-label">TODAY'S WORD</span>
                <time datetime="{iso_date}">{formatted_date}</time>
                <span class="index-mark" aria-hidden="true">01</span>
            </div>

            <div class="lesson-content">
                <p class="eyebrow">本日の熟語</p>
                <h1 id="idiom-title"><ruby>{display_word}<rp>（</rp><rt>{reading}</rt><rp>）</rp></ruby></h1>
                <p class="word-meta"><span>{part_of_speech}</span><span lang="en">Japanese WordNet 1.1</span></p>

                <section class="meaning" aria-labelledby="meaning-heading">
                    <h2 id="meaning-heading">意味</h2>
                    <p>{meaning}</p>
                </section>

                <section class="example" aria-labelledby="example-heading">
                    <h2 id="example-heading">用例</h2>
                    <blockquote>{example}</blockquote>
                </section>
            </div>
        </article>
    </main>

    <footer class="site-footer">
        <p>定義・用例の出典: <a href="https://bond-lab.github.io/wnja/jpn/index.html">日本語 WordNet</a></p>
        <p class="footer-note">
            Japanese WordNet 1.1 および pykakasi を使用しています。
            一部の読みに誤りがある場合があります。ご了承ください。
        </p>
    </footer>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate today's Japanese idiom page.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=datetime.now(TIME_ZONE).date(),
        help="Date to generate in YYYY-MM-DD format (defaults to Asia/Tokyo today).",
    )
    arguments = parser.parse_args()

    if not arguments.database.is_file():
        parser.error(f"Dictionary database not found: {arguments.database}")

    entries = load_entries(arguments.database)
    try:
        entry = select_entry(entries, arguments.date)
    except ValueError as error:
        parser.error(str(error))

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        render_page(entry, arguments.date), encoding="utf-8"
    )
    print(f"Generated {arguments.output} for {arguments.date}: {entry['display_word']}")


if __name__ == "__main__":
    main()