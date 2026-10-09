import re

from .models import Book, Series

# 末尾のレーベル表記。「(てんとう虫コミックス(少年))」のような1段の入れ子まで対応する。
_LABEL_RE = re.compile(r"\s*[(（][^()（）]*(?:[(（][^()（）]*[)）][^()（）]*)*[)）]\s*$")
# 「〔小学館文庫〕」のような亀甲括弧の注記。
_BRACKET_NOTE_RE = re.compile(r"〔[^〕]*〕")
# 末尾の巻数。「らんま1/2」の「2」を巻数と誤認しないよう、直前が「/」や数字の場合は除く。
_VOLUME_RE = re.compile(
    r"[\s　]*[(（]?\s*(?:第|vol\.?\s*|Vol\.?\s*)?(?<![/／\d])\d+\s*巻?\s*[)）]?\s*$"
)


def normalize_series_title(title: str) -> str:
    """タイトルから巻数とレーベル表記を取り除き、シリーズ名を返す。"""
    normalized = _BRACKET_NOTE_RE.sub("", title).strip()
    # 括弧書きは「(3) (ジャンプコミックス)」のように重なるので、末尾から全部外す。
    while True:
        stripped = _LABEL_RE.sub("", normalized).strip()
        if not stripped or stripped == normalized:
            break
        normalized = stripped
    # 巻数は1回だけ外す。繰り返すと「H2 1」が「H」になってしまう。
    return _VOLUME_RE.sub("", normalized).strip() or normalized


def group_series(books: list[Book]) -> list[Series]:
    """本をシリーズ単位にまとめる。プロンプトキャッシュが効くよう、並び順とidは入力が同じなら毎回同じになる。"""
    groups: dict[tuple[str, str], list[Book]] = {}
    for book in books:
        key = (normalize_series_title(book.title), book.author.strip())
        groups.setdefault(key, []).append(book)

    return [
        Series(series_id=f"s{i}", title=title, author=author, books=group)
        for i, ((title, author), group) in enumerate(sorted(groups.items()), start=1)
    ]
