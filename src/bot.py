import json
import logging
import os

import anthropic
import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from dotenv import load_dotenv

from .csv_loader import load_books
from .matcher import find_matching_series
from .models import Series
from .series import group_series

load_dotenv()

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CSV_PATH = os.environ.get("BOOKLOG_CSV_PATH", "./data/booklog_export.csv")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

logger = logging.getLogger(__name__)

anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


class BooklogBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.books = []
        self.series = []

    async def setup_hook(self):
        # CSVがなくてもBot自体は起動させ、/reload_books で後から読み込めるようにする。
        try:
            self.reload_books()
        except (OSError, UnicodeDecodeError):
            logger.exception("蔵書CSVの読み込みに失敗しました: %s", CSV_PATH)
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    def reload_books(self):
        self.books = load_books(CSV_PATH)
        self.series = group_series(self.books)


client = BooklogBot()


def _format_location(series: Series) -> str:
    locations = series.locations()
    if len(locations) == 1:
        return next(iter(locations)) or "(カテゴリ未設定)"
    return "、".join(
        f"{location or '(カテゴリ未設定)'}({count}冊)"
        for location, count in locations.most_common()
    )


@client.tree.command(
    name="book", description="自然言語で本を探して、保管場所(カテゴリ)を調べます"
)
@app_commands.describe(query="探したい本の特徴や内容(自然言語でOK)")
async def book_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not client.series:
        await interaction.followup.send(
            "蔵書データが読み込まれていません。`/reload_books` を実行してください。",
            ephemeral=True,
        )
        return

    # 例外をそのまま投げると、Discord上は「考え中…」のまま応答が返らなくなる。
    try:
        matches, _reasoning = await find_matching_series(
            anthropic_client, query, client.series
        )
    except anthropic.APIError:
        logger.exception("Claude APIの呼び出しに失敗しました")
        await interaction.followup.send(
            "検索中にエラーが発生しました。しばらくしてからもう一度お試しください。",
            ephemeral=True,
        )
        return
    except json.JSONDecodeError:
        logger.exception("Claudeの応答をJSONとして解釈できませんでした")
        await interaction.followup.send(
            "検索結果を読み取れませんでした。問い合わせの言い方を変えてお試しください。",
            ephemeral=True,
        )
        return

    if not matches:
        await interaction.followup.send(
            f"「{query}」に合致する本が見つかりませんでした。", ephemeral=True
        )
        return

    if len(matches) == 1:
        s = matches[0]
        await interaction.followup.send(
            f"**{s.title}**({s.author}・{len(s.books)}冊)\n場所: {_format_location(s)}",
            ephemeral=True,
        )
        return

    lines = [f"候補が複数見つかりました({len(matches)}件):"]
    for s in matches[:10]:
        lines.append(
            f"- {s.title}({s.author}・{len(s.books)}冊) — 場所: {_format_location(s)}"
        )
    await interaction.followup.send("\n".join(lines), ephemeral=True)


@client.tree.command(name="reload_books", description="ブクログCSVを再読み込みします")
async def reload_books_command(interaction: discord.Interaction):
    try:
        client.reload_books()
    except (OSError, UnicodeDecodeError) as e:
        logger.exception("蔵書CSVの読み込みに失敗しました: %s", CSV_PATH)
        await interaction.response.send_message(
            f"蔵書データを読み込めませんでした: {e}", ephemeral=True
        )
        return
    await interaction.response.send_message(
        f"蔵書データを再読み込みしました({len(client.books)}冊・{len(client.series)}シリーズ)。",
        ephemeral=True,
    )


def main():
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
