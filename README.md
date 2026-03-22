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
docker-compose exec app python main.py
```
