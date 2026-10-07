import os

import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from dotenv import load_dotenv

from .csv_loader import load_books
from .matcher import find_matching_books

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


client = BooklogBot()


@client.tree.command(
    name="book", description="自然言語で本を探して、保管場所(カテゴリ)を調べます"
)
@app_commands.describe(query="探したい本の特徴や内容(自然言語でOK)")
async def book_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)

    if not client.books:
        await interaction.followup.send(
            "蔵書データが読み込まれていません。`/reload_books` を実行してください。"
        )
        return

    matches, _reasoning = await find_matching_books(anthropic_client, query, client.books)

    if not matches:
        await interaction.followup.send(
            f"「{query}」に合致する本が見つかりませんでした。"
        )
        return

    if len(matches) == 1:
        b = matches[0]
        location = b.category or "(カテゴリ未設定)"
        await interaction.followup.send(f"**{b.title}**({b.author})\n場所: {location}")
        return

    lines = [f"候補が複数見つかりました({len(matches)}件):"]
    for b in matches[:10]:
        location = b.category or "(カテゴリ未設定)"
        lines.append(f"- {b.title}({b.author}) — 場所: {location}")
    await interaction.followup.send("\n".join(lines))


@client.tree.command(name="reload_books", description="ブクログCSVを再読み込みします")
async def reload_books_command(interaction: discord.Interaction):
    client.reload_books()
    await interaction.response.send_message(
        f"蔵書データを再読み込みしました({len(client.books)}件)。"
    )


def main():
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
