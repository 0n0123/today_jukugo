import argparse
import os
import sqlite3
import tempfile
import unicodedata
from pathlib import Path

from pykakasi import kakasi


POS_LABELS = {
    "n": "名詞",
    "a": "形容詞",
    "v": "サ変動詞",
}


def is_kanji_word(word):
    if not 2 <= len(word) <= 4:
        return False

    return all(
        character in {"々", "〻"}
        or unicodedata.name(character, "").startswith(
            ("CJK UNIFIED IDEOGRAPH-", "CJK COMPATIBILITY IDEOGRAPH-")
        )
        for character in word
    )


def _is_kanji_character(character):
    return character in {"々", "〻"} or unicodedata.name(character, "").startswith(
        ("CJK UNIFIED IDEOGRAPH-", "CJK COMPATIBILITY IDEOGRAPH-")
    )


def collect_idioms(source_path):
    connection = sqlite3.connect(source_path)
    converter = kakasi()
    try:
        rows = connection.execute(
            """
            SELECT word.lemma, word.pos, sense.synset, sense.freq, sense.rank,
                   (SELECT def FROM synset_def
                    WHERE synset = sense.synset AND lang = 'jpn'
                    ORDER BY sid LIMIT 1),
                   (SELECT def FROM synset_ex
                    WHERE synset = sense.synset AND lang = 'jpn'
                      AND instr(def, word.lemma) > 0
                    ORDER BY sid LIMIT 1)
            FROM word
            JOIN sense ON sense.wordid = word.wordid
            WHERE word.lang = 'jpn'
              AND sense.lang = 'jpn'
              AND word.pos IN ('n', 'a', 'v')
            """
        )

        idioms = {}
        for word, pos, synset, frequency, rank, meaning, example in rows:
            if not is_kanji_word(word) or not meaning or not example:
                continue

            display_word = f"{word}する" if pos == "v" else word
            reading = "".join(part["hira"] for part in converter.convert(display_word))
            if not reading or any(_is_kanji_character(character) for character in reading):
                continue

            entry = {
                "word": word,
                "display_word": display_word,
                "reading": reading,
                "pos": pos,
                "part_of_speech": POS_LABELS[pos],
                "synset": synset,
                "meaning": meaning,
                "example": example,
                "frequency": frequency or 0,
                "rank": rank or "",
            }
            current = idioms.get(word)
            if current is None or _sense_order(entry) < _sense_order(current):
                idioms[word] = entry

        return sorted(idioms.values(), key=lambda entry: entry["word"])
    finally:
        connection.close()


def _sense_order(entry):
    rank = entry["rank"]
    try:
        numeric_rank = int(rank)
    except (TypeError, ValueError):
        numeric_rank = 2**31
    return (-entry["frequency"], numeric_rank, entry["synset"])


def write_dictionary(idioms, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent
    )
    os.close(descriptor)

    try:
        connection = sqlite3.connect(temporary_path)
        try:
            connection.executescript(
                """
                CREATE TABLE idiom (
                    word TEXT PRIMARY KEY,
                    display_word TEXT NOT NULL,
                    reading TEXT NOT NULL,
                    pos TEXT NOT NULL,
                    part_of_speech TEXT NOT NULL,
                    synset TEXT NOT NULL,
                    meaning TEXT NOT NULL,
                    example TEXT NOT NULL
                );
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            connection.executemany(
                """
                INSERT INTO idiom
                (word, display_word, reading, pos, part_of_speech, synset, meaning, example)
                VALUES (:word, :display_word, :reading, :pos, :part_of_speech, :synset,
                        :meaning, :example)
                """,
                idioms,
            )
            connection.executemany(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                [
                    ("source", "Japanese WordNet 1.1"),
                    ("reading_converter", "pykakasi 2.3.0"),
                    ("entry_count", str(len(idioms))),
                ],
            )
            connection.commit()
            connection.execute("VACUUM")
        finally:
            connection.close()
        os.replace(temporary_path, output_path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def main():
    parser = argparse.ArgumentParser(
        description="Build a compact Japanese idiom database from Japanese WordNet."
    )
    parser.add_argument("--source", default="wnjpn.db", help="Path to the source WordNet database")
    parser.add_argument(
        "--output", default="data/idioms.sqlite3", help="Path to the compact output database"
    )
    arguments = parser.parse_args()

    if not Path(arguments.source).is_file():
        parser.error(f"Source database not found: {arguments.source}")

    idioms = collect_idioms(arguments.source)
    if not idioms:
        parser.error("No entries matched the idiom filters.")

    write_dictionary(idioms, arguments.output)
    print(f"Wrote {len(idioms):,} entries to {arguments.output}")


if __name__ == "__main__":
    main()