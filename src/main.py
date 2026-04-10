import os
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from spreadsheet import SpreadsheetManager
from scraper import InstagramScraper

def main():
    # .env ファイルの読み込み
    load_dotenv()

    # コマンドライン引数から取得投稿数を受け取る（デフォルト3）
    target_post_count = 3
    if len(sys.argv) > 1:
        try:
            target_post_count = int(sys.argv[1])
        except ValueError:
            print(f"警告: 引数 '{sys.argv[1]}' が数値ではありません。デフォルトの 3 を使用します。")

    # 環境変数の取得
    ig_username = os.getenv("INSTAGRAM_USERNAME")
    ig_password = os.getenv("INSTAGRAM_PASSWORD")
    spreadsheet_key = os.getenv("SPREADSHEET_KEY")
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    # 必須項目のチェック
    if not all([ig_username, ig_password, spreadsheet_key, service_account_file]):
        print("エラー: .env ファイルに必要な設定が不足しています。")
        sys.exit(1)

    print(f"=== Instagram Comment Scraper 起動 (取得件数: {target_post_count}) ===")

    try:
        ss_manager = SpreadsheetManager(spreadsheet_key, service_account_file)
    except Exception as e:
        print(f"初期化エラー: {e}")
        return
    
    user_ids = ss_manager.get_target_user_ids()
    if not user_ids:
        print("処理対象のユーザーIDが見つかりませんでした。")
        return

    print(f"{len(user_ids)} 名のユーザーを処理します。")

    # スクレイパーの初期化
    scraper = InstagramScraper(ig_username, ig_password)
    
    with sync_playwright() as playwright:
        try:
            if not scraper.login(playwright):
                print("ログインに失敗したため、処理を中断します。")
                return

            from datetime import datetime
            
            for user_id in user_ids:
                print(f"\n--- ユーザー処理開始: {user_id} ---")
                
                # 1. 投稿URLを取得
                print(f"最新の {target_post_count} 件の投稿を取得します...")
                post_urls, total_posts, profile_status = scraper.get_recent_post_urls(user_id, max_posts=target_post_count)
                
                if not post_urls:
                    # 投稿が見つからない、またはエラーの場合
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ss_manager.append_result(user_id, "-", "-", "-", "-", 0, 0, "", profile_status)
                    print(f"プロフィール処理結果: {profile_status}")
                    continue

                print(f"取得した {len(post_urls)} 件の投稿を巡回します...")
                
                all_rows = []
                # 2. 各投稿URLにアクセスしてコメントユーザーを抽出
                for post_url in post_urls:
                    commenter_ids, comment_status = scraper.get_commenting_users(post_url, user_id)
                    
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if commenter_ids:
                        for cid in commenter_ids:
                            # ユーザーIDからプロフィールURLを生成
                            user_url = f"https://www.instagram.com/{cid}/"
                            # プロフィール情報を一括取得（非公開判定、フォロワー数、フォロー数、Bio）
                            account_status, followers, following, bio = scraper.get_profile_info(cid)
                            all_rows.append([now, user_id, post_url, cid, user_url, account_status, followers, following, bio, "成功"])
                    else:
                        # コメントがない場合も1行記録（またはスキップの判断も可。ここでは記録する）
                        all_rows.append([now, user_id, post_url, "-", "-", "-", 0, 0, "", comment_status])
                
                # 3. スプレッドシートへ一括書き込み
                if all_rows:
                    if ss_manager.append_results(all_rows):
                        print(f"結果を {len(all_rows)} 件記録しました。")
                    else:
                        print("スプレッドシートへの記録に失敗しました。")
                else:
                    print("記録するデータがありませんでした。")

        except Exception as e:
            print(f"メインループ内で予期せぬエラーが発生しました: {e}")
        finally:
            # 正常終了時もエラー発生時も必ずトレースを保存してブラウザを閉じる
            scraper.stop_tracing()
            scraper.close()

    print("\n=== 全ての処理が完了しました ===")

if __name__ == "__main__":
    main()
