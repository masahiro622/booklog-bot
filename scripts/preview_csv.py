"""実際のブクログCSVが正しくパースできているか確認するための簡易スクリプト。

使い方:
    python scripts/preview_csv.py path/to/booklog_export.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.csv_loader import load_books  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("使い方: python scripts/preview_csv.py <CSVパス>")
        raise SystemExit(1)

    books = load_books(sys.argv[1])
    print(f"{len(books)} 件読み込みました。先頭5件:")
    for b in books[:5]:
        print(f"- title={b.title!r} author={b.author!r} category={b.category!r} tags={b.tags!r}")


if __name__ == "__main__":
    main()
