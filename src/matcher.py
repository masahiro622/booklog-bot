import json

from anthropic import AsyncAnthropic

from .models import Series

_MODEL = "claude-sonnet-5-5"

_INSTRUCTIONS = """\
あなたは個人の蔵書から本を探す手伝いをします。
後に続く「蔵書一覧」は、持っている本をシリーズ単位にまとめたもので、各行は
「id<TAB>タイトル<TAB>著者<TAB>冊数」です。

ユーザーの問い合わせに当てはまるシリーズを蔵書一覧から選び、そのidを matches に入れてください。
- 問い合わせはタイトルや著者名とは限りません。「バスケのマンガ」「泣ける話」のような内容や
  雰囲気での問い合わせには、作品について知っていることを使って当てはまるものを選んでください。
- 蔵書一覧にないidは返さないでください。当てはまるものがなければ matches は空にしてください。
- 1つに絞れない場合は複数返してかまいませんが、当てはまりそうな順に最大10件までにしてください。
- reasoning には選んだ理由を日本語で簡潔に書いてください。
"""

_OUTPUT_FORMAT = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "matches": {
                "type": "array",
                "items": {"type": "string"},
                "description": "蔵書一覧のidのうち、問い合わせに当てはまるもの",
            },
            "reasoning": {
                "type": "string",
                "description": "簡潔な選定理由(日本語)",
            },
        },
        "required": ["matches", "reasoning"],
        "additionalProperties": False,
    },
}


def _build_catalog(series_list: list[Series]) -> str:
    # 毎回同じ文字列になるようにする(プロンプトキャッシュはバイト単位の前方一致)。
    lines = [
        "\t".join(
            (s.series_id, s.title, s.author or "(著者不明)", f"{len(s.books)}冊")
        )
        for s in series_list
    ]
    return "## 蔵書一覧\n" + "\n".join(lines)


async def find_matching_series(
    client: AsyncAnthropic, query: str, series_list: list[Series]
) -> tuple[list[Series], str | None]:
    if not series_list:
        return [], None

    response = await client.beta.messages.create(
        model=_MODEL,
        max_tokens=16000,
        # 拒否された場合は、拒否の種類に応じた別モデルでサーバー側が再実行する。
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": _OUTPUT_FORMAT},
        system=[
            {"type": "text", "text": _INSTRUCTIONS},
            {
                "type": "text",
                "text": _build_catalog(series_list),
                # 蔵書一覧は数万トークンあるので、連続した問い合わせではキャッシュから読ませる。
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": query}],
    )

    if response.stop_reason == "refusal":
        return [], None

    text = next(
        (block.text for block in reversed(response.content) if block.type == "text"),
        None,
    )
    if text is None:
        return [], None

    result = json.loads(text)
    by_id = {s.series_id: s for s in series_list}
    matched = [by_id[i] for i in result.get("matches", []) if i in by_id]
    return matched, result.get("reasoning")
