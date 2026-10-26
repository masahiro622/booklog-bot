# booklog-bot

ブクログの蔵書CSV(手動エクスポート)を読み込み、Discord上で自然言語で「〇〇っぽい本どこ?」と聞くと、
LLM(Claude)が蔵書リストの中から該当しそうな本を選び、CSVの「カテゴリ」列(=保管場所)を返すBot。

<img src="docs/screenshot.jpg" alt="Discordでの実行例。「バスケ」と聞くと、タイトルに「バスケ」を含まない『THE FIRST SLAM DUNK re:SOURCE』とその保管場所が返る" width="480">

## 作った理由

手元の蔵書が約4,600冊あり、ブクログで管理して「カテゴリ」に棚の場所を入れているものの、
「あのバスケのマンガどこに置いたっけ」のようにタイトルがうろ覚えだとブクログの検索では見つけられなかった。
同居人も使えるよう、普段使っているDiscordから自然な言葉で聞けるようにした。

## 工夫した点

- **全件をLLMに渡せる量に圧縮する**: 巻数・レーベル表記を正規表現で外して「シリーズ名+著者」単位にまとめ、
  約4,600冊を約1,300件にした。検索用のインデックスやベクトルDBを用意せずに済み、
  タイトルの文字が一致しない「バスケのマンガ」のような問い合わせにもClaudeの作品知識で答えられる。
- **プロンプトキャッシュが効くようにする**: シリーズ一覧(数万トークン)はキャッシュ対象にしている。
  キャッシュは前方一致なので、入力CSVの並び順に関係なく一覧の文字列とidが毎回同じになるようにした。
- **LLMの出力を構造化して検証する**: Structured Outputs(JSON Schema)でidの配列を返させ、
  蔵書一覧に存在しないidは捨てる。LLMが架空の本を答えても、その本はユーザーに返らない。
- **タイトル中の数字を巻数と誤認しない**: 「らんま1/2」「H2」「HUNTER X HUNTER10」など、
  実データで見つかった紛らわしいタイトルをテストケースにしている(`tests/test_series.py`)。
- **当初はあいまい文字列検索だった**: 表記ゆれには強いが内容での問い合わせに答えられなかったため、
  シリーズ単位にまとめてLLMに選ばせる方式に切り替えた。

## 構成

```
src/
  bot.py         Discordのスラッシュコマンド
  csv_loader.py  ブクログCSV(CP932・ヘッダーなし17列)の読み込み
  series.py      タイトルの正規化とシリーズ単位へのまとめ
  matcher.py     Claudeに蔵書一覧と問い合わせを渡して該当シリーズを選ばせる
tests/           pytestによるテスト(Claude APIはフェイクに差し替え)
```

## 仕組み

1. ブクログのPC版サイトの本棚エクスポート機能でCSVを手動ダウンロードし、`data/booklog_export.csv` に置く。
2. Bot起動時(または `/reload_books` 実行時)にCSVを読み込み、巻数・レーベル表記を除いた
   「シリーズ名+著者」単位にまとめてメモリ上に保持する(`src/series.py`)。
3. Discordで `/book query:<自然言語>` を実行すると、
   - シリーズ一覧をすべてClaudeに渡して該当するシリーズ(0〜複数件)を特定し、
   - 該当シリーズのカテゴリ(保管場所)を返信する。巻ごとに場所が分かれている場合は場所ごとの冊数も返す。

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

CSVを用意する前に動作だけ確認したい場合は、`BOOKLOG_CSV_PATH=./data/booklog_export.sample.csv` を指定すると
架空の本5冊のサンプルで動かせる。

## テスト

```bash
pip install -r requirements-dev.txt
pytest
```

## Discordでの使い方

- `/book query:東野圭吾のミステリー` — 自然言語で本を検索し、見つかった本の保管場所を返信。
- `/reload_books` — CSVを更新した後、再読み込みして反映する。

## 運用メモ

- CSVは手動更新前提。本を配置換えしたら、ブクログ側でカテゴリを更新 → CSVを再エクスポート →
  `data/booklog_export.csv` を上書き → Discordで `/reload_books` の流れで反映する。
- シリーズ単位にまとめることで、約4,600冊の蔵書が約1,300件の一覧になり、毎回全件をClaudeに渡せる量に収まる。
  タイトルの文字が一致しない「バスケのマンガ」のような問い合わせにも、Claudeの作品知識で答えられる。
- シリーズ一覧はプロンプトキャッシュ(5分)の対象にしているため、続けて問い合わせると2回目以降は安く速くなる。
- シリーズのまとめ方は正規表現による推定なので、まとめ方がおかしいシリーズがあれば `src/series.py` を調整する。
