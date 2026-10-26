import json

from anthropic import AsyncAnthropic
from rapidfuzz import fuzz, process

from .models import Book

_SELECT_TOOL = {
    "name": "select_books",
    "description": (
        "ユーザーの自然言語の問い合わせに最も合致する本を、候補リストの中からidで選ぶ。"
        "合致するものがなければ matches を空配列にする。"
        "複数の本が同程度に当てはまり一つに絞れない場合は複数返してよい。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "matches": {
                "type": "array",
                "items": {"type": "string"},
                "description": "候補リストのidのうち、問い合わせに合致するもの",
            },
            "reasoning": {
                "type": "string",
                "description": "簡潔な選定理由(日本語)",
            },
        },
        "required": ["matches"],
    },
}

_PREFILTER_LIMIT = 40
_MODEL = "claude-sonnet-5-5"


def _prefilter(query: str, books: list[Book]) -> list[Book]:
    if len(books) <= _PREFILTER_LIMIT:
        return books

    choices = {book.item_id: book.search_text() for book in books}
    results = process.extract(
        query, choices, scorer=fuzz.WRatio, limit=_PREFILTER_LIMIT
    )
    matched_ids = {item_id for _, _score, item_id in results}
    return [book for book in books if book.item_id in matched_ids]


async def find_matching_books(
    client: AsyncAnthropic, query: str, books: list[Book]
) -> tuple[list[Book], str | None]:
    candidates = _prefilter(query, books)
    if not candidates:
        return [], None

    candidate_payload = [
        {
            "id": book.item_id,
            "title": book.title,
            "author": book.author,
            "genre": book.genre,
            "tags": book.tags,
        }
        for book in candidates
    ]

    response = await client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        tools=[_SELECT_TOOL],
        tool_choice={"type": "tool", "name": "select_books"},
        messages=[
            {
                "role": "user",
                "content": (
                    "以下は書籍候補リストです(JSON配列)。ユーザーの問い合わせに最も合致する本を"
                    "select_booksツールで回答してください。\n\n"
                    f"問い合わせ: {query}\n\n"
                    f"候補リスト:\n{json.dumps(candidate_payload, ensure_ascii=False)}"
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "select_books":
            matched_ids = set(block.input.get("matches", []))
            reasoning = block.input.get("reasoning")
            matched_books = [b for b in candidates if b.item_id in matched_ids]
            return matched_books, reasoning

    return [], None
