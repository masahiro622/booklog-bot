from pathlib import Path

import pytest

from src.csv_loader import load_books

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "data" / "booklog_export.sample.csv"


def test_load_sample_csv():
    books = load_books(str(SAMPLE_CSV))

    assert len(books) == 5
    first = books[0]
    assert first.title == "架空の冒険 1 (サンプルコミックス)"
    assert first.author == "山田太郎"
    assert first.category == "A1-1"
    assert first.isbn == "9784000000011"


def test_load_books_fills_missing_columns_with_empty_string(tmp_path):
    csv_path = tmp_path / "short.csv"
    csv_path.write_text('"1","2","978","棚A"\n', encoding="cp932")

    [book] = load_books(str(csv_path))

    assert book.category == "棚A"
    assert book.title == ""


def test_load_books_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_books(str(tmp_path / "nothing.csv"))
