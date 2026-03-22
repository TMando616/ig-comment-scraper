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

    print("=== Instagram Comment Scraper (Latest Post) 起動 ===")

    try:
        # スプレッドシートマネージャーの初期化
        ss_manager = SpreadsheetManager(spreadsheet_key, service_account_file)
    except Exception as e:
        print(f"初期化エラー: {e}")
        return
    
    # ターゲットユーザーIDの取得
    user_ids = ss_manager.get_target_user_ids()
    if not user_ids:
        print("処理対象のユーザーIDが見つかりませんでした。")
        return

    print(f"{len(user_ids)} 名のユーザーを処理します。")

    # スクレイパーの初期化
    scraper = InstagramScraper(ig_username, ig_password)
    
    with sync_playwright() as playwright:
        if not scraper.login(playwright):
            print("ログインに失敗したため、処理を中断します。")
            return

        for user_id in user_ids:
            print(f"\n--- ユーザー処理開始: {user_id} ---")
            
            # 1. 最新投稿URLの取得
            post_url, status = scraper.get_latest_post_url(user_id)
            
            comment_count = "-"
            if post_url:
                # 2. コメント数の取得
                count, comment_status = scraper.get_comment_count(post_url)
                if count is not None:
                    comment_count = count
                    status = "成功"
                else:
                    status = comment_status
            else:
                # 投稿URLが取得できなかった場合は、その理由がstatusに入っている
                post_url = "-"
            
            # 3. 結果を「出力結果」シートに追記
            if ss_manager.append_result(user_id, post_url, comment_count, status):
                print(f"結果を記録しました: {status}")
            else:
                print(f"結果の記録に失敗しました。")

        scraper.close()

    print("\n=== 全ての処理が完了しました ===")

if __name__ == "__main__":
    main()
