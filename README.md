# booklog-bot

ブクログの蔵書CSV(手動エクスポート)を読み込み、Discord上で自然言語で「〇〇っぽい本どこ?」と聞くと、
LLM(Claude)が蔵書リストの中から該当しそうな本を選び、CSVの「カテゴリ」列(=保管場所)を返すBot。

## 仕組み

1. ブクログのPC版サイトの本棚エクスポート機能でCSVを手動ダウンロードし、`data/booklog_export.csv` に置く。
2. Bot起動時(または `/reload_books` 実行時)にCSVを読み込み、メモリ上に保持する。
3. Discordで `/book query:<自然言語>` を実行すると、
   - 候補が多い場合はタイトル・著者・ジャンル・タグに対する簡易あいまい検索で候補を絞り込み、
   - 絞り込んだ候補リストをClaudeに渡して該当する本(0〜複数件)を特定し、
   - 該当本のカテゴリ(保管場所)を返信する。

## セットアップ

### 1. 依存関係のインストール

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Discord Bot の作成

1. https://discord.com/developers/applications で新規アプリケーションを作成。
2. 「Bot」タブでBotを追加し、トークンを発行(これが `DISCORD_BOT_TOKEN`)。
3. 「OAuth2 > URL Generator」で scope に `bot` と `applications.commands` をチェックし、
   生成されたURLで自分のサーバーにBotを招待する。

### 3. Anthropic API キーの取得

https://console.anthropic.com で発行したキーを `ANTHROPIC_API_KEY` に設定する。

### 4. 環境変数の設定

`.env.example` を `.env` にコピーして値を埋める。

```bash
copy .env.example .env
```

### 5. ブクログCSVの配置

ブクログPC版サイトの本棚メニュー(設定アイコンなど)から「エクスポート」を実行してCSVをダウンロードし、
`data/booklog_export.csv` として保存する(このファイルは `.gitignore` 済み)。

### 6. Bot起動

```bash
python -m src.bot
```

## Discordでの使い方

- `/book query:東野圭吾のミステリー` — 自然言語で本を検索し、見つかった本の保管場所を返信。
- `/reload_books` — CSVを更新した後、再読み込みして反映する。

## 運用メモ

- CSVは手動更新前提。本を配置換えしたら、ブクログ側でカテゴリを更新 → CSVを再エクスポート →
  `data/booklog_export.csv` を上書き → Discordで `/reload_books` の流れで反映する。
- 蔵書数が多い場合、候補の絞り込み(あいまい検索)を経てからLLMに渡す設計にしているため、
  数千冊規模でもLLMへの入力トークン量は一定範囲に収まる(`src/matcher.py` の `_PREFILTER_LIMIT`)。
