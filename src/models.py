from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Book:
    item_id: str
    isbn: str
    category: str
    rating: str
    status: str
    tags: str
    registered_at: str
    title: str
    author: str
    publisher: str
    pub_year: str
    genre: str


@dataclass
class Series:
    """巻数・レーベル表記を除いたタイトルと著者でまとめた本のグループ。"""

    series_id: str
    title: str
    author: str
    books: list[Book] = field(default_factory=list)

    def locations(self) -> Counter[str]:
        """保管場所ごとの冊数。カテゴリ未設定の本は空文字で数える。"""
        return Counter(book.category for book in self.books)
