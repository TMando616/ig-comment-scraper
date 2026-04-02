# Instagram Comment Scraper Prototype

## プロジェクトの目的
Instagramの特定の投稿URLからコメント数を取得し、Googleスプレッドシートに自動で反映させるプロトタイプです。

## プロジェクト構成
- `main.py`: メインの実行フロー
- `scraper.py`: Playwrightを使用したInstagramのログイン・スクレイピング処理
- `spreadsheet.py`: gspreadを使用したGoogleスプレッドシートの読み書き
- `config.py`: 環境変数の読み込み設定
- `Dockerfile`: 実行環境の定義
- `docker-compose.yml`: コンテナ実行の定義

## 環境構築手順

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd ig-comment-scraper
```

### 2. 環境変数の設定
`.env.example` をコピーして `.env` を作成し、必要な情報を入力してください。
```bash
cp .env.example .env
```
※ Googleスプレッドシート操作用のサービスアカウントキー（JSON）もプロジェクトルートに配置してください。

### 3. Dockerコンテナの起動
```bash
docker-compose up -d --build
```

## 実行方法
コンテナ内でメイン処理を実行します。
```bash
docker-compose run --rm app python src/main.py
```

## 詳細な実装内容

### 1. メインロジック (`src/main.py`)
- `.env` から認証情報（Instagram, Google Sheets）を読み込みます。
- `SpreadsheetManager` を初期化し、スプレッドシートの「ターゲット」シートから処理対象のユーザーIDを取得します。
- `InstagramScraper` を初期化し、Playwright を用いて Instagram にログインします。
- 各ユーザーIDに対して以下の順序で処理を行い、結果をスプレッドシートの「出力結果」シートに記録します。
  1. ユーザープロフィールの総投稿数と最新最大10件の投稿URLを取得
  2. 各投稿詳細ページを巡回し、コメント投稿者のユーザーIDを取得
  3. 取得した全コメントユーザーIDをスプレッドシートに一括追記

### 2. Instagramスクレイピング (`src/scraper.py`)
- **ログイン機能**:
  - `state.json` を使用してブラウザのセッション情報を保存・再利用します。
  - プロジェクトルートに `state.json` が存在する場合、`browser.new_context(storage_state=...)` を使用してログイン画面をスキップします。
  - **クッキーの自動補正**: `state.json` 読み込み時に、Playwright が要求する形式（Strict, Lax, None）に `sameSite` 属性を自動的にクレンジングする機能を実装。これにより、外部ツールで書き出されたセッション情報の読み込みエラーを回避します。
  - ログイン済みかどうかの判定は、ホームアイコンや検索アイコン等の存在を確認することで行います。
  - セッションが無効な場合やファイルが存在しない場合は、ユーザー名・パスワードを自動入力してログインを試行するフォールバック処理を実装しています。
  - ログインボタン押下後の待機時間を最大60秒（従来の3倍）に延長し、ネットワーク遅延や認証処理に柔軟に対応します。
- **データ取得ロジック**:
  - `get_post_count`: プロフィール画面のヘッダーから総投稿数を抽出します。
  - `get_recent_post_urls`: 指定ユーザーのプロフィールページから、最新最大10件の投稿URL（`/p/` または `/reel/`）を取得します。
  - `get_commenting_users`: 指定された投稿URLから、コメントしているユーザーのIDリストを抽出します（投稿者本人は除外）。
  - `get_comment_count`: 投稿ページ内の特定の要素（`span[role="button"].x1ypdohk` 等）のテキストから、正規表現を用いてコメント数を抽出します。要素が見つからない場合や取得エラー時は、安全に `0` を返す例外処理を実装しています。
- **デバッグ機能**:
  - 各ステップでスクリーンショットを `debug/` ディレクトリに保存します。
  - Playwright の `Tracing` 機能を有効化しており、エラー発生時の詳細な調査が可能です。

### 3. スプレッドシート管理 (`src/spreadsheet.py`)
- `gspread` ライブラリを使用して Google Sheets API と連携します。
- **ターゲットシート**: A列（1行目はヘッダー）からユーザーIDを取得します。
- **出力結果シート**: [取得日時, ターゲットID, 投稿URL, コメントしたユーザーのID, ステータス] の形式で追記します。
- `append_results`: 複数の行を一括で追記するメソッドを実装。
