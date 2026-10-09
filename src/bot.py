import os

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

anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


class BooklogBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.books = []
        self.series = []

    async def setup_hook(self):
        self.reload_books()
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
    await interaction.response.defer(thinking=True)

    if not client.series:
        await interaction.followup.send(
            "蔵書データが読み込まれていません。`/reload_books` を実行してください。"
        )
        return

    matches, _reasoning = await find_matching_series(
        anthropic_client, query, client.series
    )

    if not matches:
        await interaction.followup.send(
            f"「{query}」に合致する本が見つかりませんでした。"
        )
        return

    if len(matches) == 1:
        s = matches[0]
        await interaction.followup.send(
            f"**{s.title}**({s.author}・{len(s.books)}冊)\n場所: {_format_location(s)}"
        )
        return

    lines = [f"候補が複数見つかりました({len(matches)}件):"]
    for s in matches[:10]:
        lines.append(
            f"- {s.title}({s.author}・{len(s.books)}冊) — 場所: {_format_location(s)}"
        )
    await interaction.followup.send("\n".join(lines))


@client.tree.command(name="reload_books", description="ブクログCSVを再読み込みします")
async def reload_books_command(interaction: discord.Interaction):
    client.reload_books()
    await interaction.response.send_message(
        f"蔵書データを再読み込みしました({len(client.books)}冊・{len(client.series)}シリーズ)。"
    )


def main():
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
