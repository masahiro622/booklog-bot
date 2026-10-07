import csv
from pathlib import Path

from .models import Book

# ブクログのCSVエクスポートはヘッダー行なし・全項目ダブルクォート囲みの固定17列。
# サービスID, アイテムID, 13桁ISBN, カテゴリ, 評価, 読書状況, レビュー, タグ,
# 非公開メモ, 登録日時, 読了日時, タイトル, 作者名, 出版社名, 発行年, ジャンル, ページ数
_FIELDS = [
    "service_id",
    "item_id",
    "isbn",
    "category",
    "rating",
    "status",
    "review",
    "tags",
    "memo",
    "registered_at",
    "finished_at",
    "title",
    "author",
    "publisher",
    "pub_year",
    "genre",
    "page_count",
]


def load_books(csv_path: str) -> list[Book]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSVが見つかりません: {csv_path}")

    # ブクログのCSVエクスポートはCP932(Shift-JIS)固定。
    text = path.read_text(encoding="cp932")
    books = []
    for row in csv.reader(text.splitlines()):
        values = {
            field: (row[i] if i < len(row) else "") for i, field in enumerate(_FIELDS)
        }
        books.append(
            Book(
                item_id=values["item_id"],
                isbn=values["isbn"],
                category=values["category"],
                rating=values["rating"],
                status=values["status"],
                tags=values["tags"],
                registered_at=values["registered_at"],
                title=values["title"],
                author=values["author"],
                publisher=values["publisher"],
                pub_year=values["pub_year"],
                genre=values["genre"],
            )
        )
    return books
