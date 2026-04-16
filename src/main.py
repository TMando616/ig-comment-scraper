import sys
from datetime import datetime
from playwright.sync_api import sync_playwright
from config import Config
from spreadsheet import SpreadsheetManager
from scraper import InstagramScraper

def main():
    # 設定の検証
    try:
        Config.validate()
    except ValueError as e:
        print(f"エラー: {e}")
        sys.exit(1)

    # コマンドライン引数から取得投稿数を受け取る（デフォルトは Config.DEFAULT_TARGET_POST_COUNT）
    target_post_count = Config.DEFAULT_TARGET_POST_COUNT
    if len(sys.argv) > 1:
        try:
            target_post_count = int(sys.argv[1])
        except ValueError:
            print(f"警告: 引数 '{sys.argv[1]}' が数値ではありません。デフォルトの {target_post_count} を使用します。")

    print(f"=== Instagram Comment Scraper 起動 (取得件数: {target_post_count}) ===")
    print(f"設定: ターゲットシート='{Config.TARGET_SHEET_NAME}', 出力結果シート='{Config.RESULT_SHEET_NAME}'")

    try:
        ss_manager = SpreadsheetManager(
            Config.SPREADSHEET_KEY, 
            Config.GOOGLE_SERVICE_ACCOUNT_FILE, 
            target_sheet_name=Config.TARGET_SHEET_NAME, 
            result_sheet_name=Config.RESULT_SHEET_NAME
        )
    except Exception as e:
        print(f"初期化エラー: {e}")
        return
    
    user_ids = ss_manager.get_target_user_ids()
    if not user_ids:
        print("処理対象のユーザーIDが見つかりませんでした。")
        return

    print(f"{len(user_ids)} 名のユーザーを処理します。")

    # スクレイパーの初期化
    scraper = InstagramScraper(
        Config.INSTAGRAM_USERNAME, 
        Config.INSTAGRAM_PASSWORD,
        state_file=Config.STATE_FILE,
        debug_dir=Config.DEBUG_DIR
    )
    
    with sync_playwright() as playwright:
        try:
            if not scraper.login(playwright):
                print("ログインに失敗したため、処理を中断します。")
                return

            for user_id in user_ids:
                print(f"\n--- ユーザー処理開始: {user_id} ---")
                
                # 1. 投稿URLを取得
                print(f"最新の {target_post_count} 件の投稿を取得します...")
                post_urls, total_posts, profile_status = scraper.get_recent_post_urls(user_id, max_posts=target_post_count)
                
                if not post_urls:
                    # 投稿が見つからない、またはエラーの場合
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ss_manager.append_result(user_id, "-", "-", "-", "-", "-", "-", 0, 0, "", profile_status)
                    print(f"プロフィール処理結果: {profile_status}")
                    continue

                print(f"取得した {len(post_urls)} 件の投稿を巡回します...")
                
                all_rows = []
                # 2. 各投稿URLにアクセスしてコメントユーザーを抽出
                for post_url in post_urls:
                    comment_data, comment_status = scraper.get_commenting_users(post_url, user_id)
                    
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if comment_data:
                        for entry in comment_data:
                            cid = entry["user_id"]
                            c_text = entry["comment_text"]
                            # ユーザーIDからプロフィールURLを生成
                            user_url = f"https://www.instagram.com/{cid}/"
                            # プロフィール情報を一括取得（非公開判定、フォロワー数、フォロー数、Bio）
                            account_status, followers, following, bio = scraper.get_profile_info(cid)
                            all_rows.append([now, user_id, post_url, cid, c_text, user_url, account_status, followers, following, bio, "成功"])
                    else:
                        # コメントがない場合も1行記録
                        all_rows.append([now, user_id, post_url, "-", "-", "-", "-", 0, 0, "", comment_status])
                
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
