import os
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from spreadsheet import SpreadsheetManager
from scraper import InstagramScraper

def main():
    # .env ファイルの読み込み
    load_dotenv()

    # 環境変数の取得
    ig_username = os.getenv("INSTAGRAM_USERNAME")
    ig_password = os.getenv("INSTAGRAM_PASSWORD")
    spreadsheet_key = os.getenv("SPREADSHEET_KEY")
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    # 必須項目のチェック
    if not all([ig_username, ig_password, spreadsheet_key, service_account_file]):
        print("エラー: .env ファイルに必要な設定が不足しています。")
        sys.exit(1)

    print("=== Instagram Comment Scraper 起動 ===")

    # スプレッドシートマネージャーの初期化
    ss_manager = SpreadsheetManager(spreadsheet_key, service_account_file)
    
    # 処理対象URLの取得
    targets = ss_manager.get_target_urls()
    if not targets:
        print("処理対象のURLが見つかりませんでした。")
        return

    print(f"{len(targets)} 件の投稿を処理します。")

    # スクレイパーの初期化とログイン
    scraper = InstagramScraper(ig_username, ig_password)
    
    with sync_playwright() as playwright:
        if not scraper.login(playwright):
            print("ログインに失敗したため、処理を中断します。")
            return

        # 各投稿のコメント数を取得して更新
        for record in targets:
            url = record.get('URL') or record.get('url')
            row_index = record.get('row_index')

            if not url:
                print(f"警告: {row_index}行目にURLが指定されていません。スキップします。")
                continue

            print(f"\n[{row_index}行目] 処理開始: {url}")
            
            # コメント数の取得
            comment_count = scraper.get_comment_count(url)
            
            if comment_count is not None:
                # スプレッドシートの更新
                if ss_manager.update_comment_count(row_index, comment_count):
                    print(f"成功: {row_index}行目を更新しました（コメント数: {comment_count}）")
                else:
                    print(f"失敗: {row_index}行目の更新に失敗しました。")
            else:
                print(f"失敗: {row_index}行目のコメント数取得に失敗しました。")

        scraper.close()

    print("\n=== 全ての処理が完了しました ===")

if __name__ == "__main__":
    main()
