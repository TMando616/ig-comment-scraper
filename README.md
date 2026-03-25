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
- 各ユーザーIDに対して以下の順序で処理を行い、結果をスプレッドシートの「出力結果」シートに追記します。
  1. ユーザープロフィールの最新投稿URL取得
  2. 投稿詳細ページからのコメント数取得
  3. 処理結果（成功/失敗理由）の記録

### 2. Instagramスクレイピング (`src/scraper.py`)
- **ログイン機能**:
  - `state.json` を使用してブラウザのセッション情報を保存・再利用します。
  - 初回またはセッション切れの場合は、フォームにユーザー名・パスワードを自動入力してログインします。
- **データ取得ロジック**:
  - `get_latest_post_url`: 指定ユーザーのプロフィールページにアクセスし、最新の `/p/` または `/reel/` リンクを抽出します。
  - `get_comment_count`: `og:description` メタタグの正規表現マッチングによりコメント数を抽出します。
- **デバッグ機能**:
  - 各ステップでスクリーンショットを `debug/` ディレクトリに保存します。
  - Playwright の `Tracing` 機能を有効化しており、エラー発生時の詳細な調査が可能です。

### 3. スプレッドシート管理 (`src/spreadsheet.py`)
- `gspread` ライブラリを使用して Google Sheets API と連携します。
- **ターゲットシート**: A列（1行目はヘッダー）からユーザーIDを取得します。
- **出力結果シート**: [取得日時, ターゲットID, 投稿URL, コメント数, ステータス] の形式で1行ずつ追記します。
