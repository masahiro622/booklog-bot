import pytest

from src.models import Book
from src.series import group_series, normalize_series_title


def _book(title: str, author: str = "著者", category: str = "") -> Book:
    return Book(
        item_id="",
        isbn="",
        category=category,
        rating="",
        status="",
        tags="",
        registered_at="",
        title=title,
        author=author,
        publisher="",
        pub_year="",
        genre="",
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        # 巻数+レーベル
        ("ラブライブ!(1) (電撃コミックス)", "ラブライブ!"),
        ("鋼の錬金術師（５）", "鋼の錬金術師"),
        ("SLAM DUNK 第12巻", "SLAM DUNK"),
        ("ONE PIECE vol.3", "ONE PIECE"),
        ("ONE PIECE Vol 3", "ONE PIECE"),
        ("HUNTER X HUNTER10", "HUNTER X HUNTER"),
        # 入れ子のレーベル表記
        ("ドラえもん 3 (てんとう虫コミックス(少年))", "ドラえもん"),
        # 亀甲括弧の注記
        ("〔小学館文庫〕容疑者Xの献身", "容疑者Xの献身"),
        # 単巻のレーベルだけ外す
        ("三体 (ハヤカワ文庫SF)", "三体"),
        # タイトルの一部である数字は残す
        ("らんま1/2", "らんま1/2"),
        ("らんま1/2 5 (少年サンデーコミックス)", "らんま1/2"),
        ("H2", "H2"),
        ("H2 1 (少年サンデーコミックス)", "H2"),
        ("コミックマーケット C93", "コミックマーケット C93"),
        ("1984", "1984"),
        # すべて外すと空になる場合は元のまま
        ("(1)", "(1)"),
    ],
)
def test_normalize_series_title(title, expected):
    assert normalize_series_title(title) == expected


def test_group_series_merges_volumes_by_title_and_author():
    books = [
        _book("架空の冒険 1 (サンプルコミックス)", "山田太郎", "A1-1"),
        _book("架空の冒険 2 (サンプルコミックス)", "山田太郎", "B2-3"),
        _book("架空の冒険 1", "別の著者"),
    ]

    series = group_series(books)

    assert [(s.title, s.author, len(s.books)) for s in series] == [
        ("架空の冒険", "別の著者", 1),
        ("架空の冒険", "山田太郎", 2),
    ]
    assert series[1].locations() == {"A1-1": 1, "B2-3": 1}


def test_group_series_is_deterministic_regardless_of_input_order():
    # プロンプトキャッシュを効かせるため、入力の順番が違っても同じidと並びになること。
    books = [_book("B 1"), _book("A 1"), _book("B 2")]

    first = group_series(books)
    second = group_series(list(reversed(books)))

    assert [(s.series_id, s.title) for s in first] == [
        (s.series_id, s.title) for s in second
    ]
