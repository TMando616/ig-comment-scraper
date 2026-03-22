import os
import time
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional

class InstagramScraper:
    """
    Instagramのスクレイピングを担当するクラス
    """
    def __init__(self, username: str, password: str, state_file: str = "state.json"):
        self.username = username
        self.password = password
        self.state_file = state_file
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    def login(self, playwright) -> bool:
        """
        Instagramにログインする。既存のセッションがあれば再利用する。
        """
        try:
            self.browser = playwright.chromium.launch(headless=True)
            
            # 保存済みのセッション情報があるか確認
            if os.path.exists(self.state_file):
                print("既存のセッションを使用してログインを試みます...")
                self.context = self.browser.new_context(storage_state=self.state_file)
            else:
                print("新規ログインを開始します...")
                self.context = self.browser.new_context()

            page = self.context.new_page()
            page.goto("https://www.instagram.com/")

            # ログインが必要か判定（ユーザー名入力フィールドがあるか）
            if page.query_selector('input[name="username"]'):
                print("ログイン情報を入力中...")
                page.fill('input[name="username"]', self.username)
                page.fill('input[name="password"]', self.password)
                page.click('button[type="submit"]')
                
                # ログイン完了を待機（プロフィール画像やホーム画面の要素を待つ）
                page.wait_for_load_state("networkidle")
                time.sleep(5)  # 念のための待機

                # セッション情報を保存
                self.context.storage_state(path=self.state_file)
                print("セッション情報を保存しました。")
            else:
                print("既にログイン状態です。")
            
            return True
        except Exception as e:
            print(f"ログイン処理中にエラーが発生しました: {e}")
            return False

    def get_comment_count(self, post_url: str) -> Optional[int]:
        """
        指定された投稿URLからコメント数を取得する
        """
        if not self.context:
            print("エラー: ログインが完了していません。")
            return None

        page: Page = self.context.new_page()
        try:
            print(f"URLにアクセス中: {post_url}")
            page.goto(post_url)
            page.wait_for_load_state("networkidle")
            time.sleep(3)  # 動的コンテンツの読み込み待機

            # コメント数を取得（セレクターはInstagramの仕様変更により変わる可能性があります）
            # ここでは「コメント数」が表示されている要素を探す
            # 例: メタタグから取得する、または画面上のテキストから抽出する
            
            # 方法1: メタタグ（og:description）から取得を試みる
            meta_desc = page.get_attribute('meta[property="og:description"]', 'content')
            if meta_desc:
                # 文字列例: "123 Comments, 456 Likes - ..."
                # 日本語の場合: "「いいね！」123件、コメント456件 - ..."
                import re
                match = re.search(r'(\d+)\s*件のコメント', meta_desc) or re.search(r'(\d+)\s*Comments', meta_desc)
                if match:
                    count = int(match.group(1))
                    print(f"コメント数を取得しました: {count}")
                    return count

            # 方法2: 画面上の要素から取得（フォールバック）
            # span等に含まれるテキストを検索（より詳細なセレクター指定が必要な場合あり）
            print("メタタグから取得できなかったため、画面上の要素を検索します...")
            # 注意: セレクターは変更されやすいため、エラーハンドリングを重視
            return 0 # 見つからない場合は暫定的に0を返すか、例外処理

        except Exception as e:
            print(f"コメント数取得中にエラーが発生しました ({post_url}): {e}")
            return None
        finally:
            page.close()

    def close(self):
        """
        ブラウザを閉じる
        """
        if self.browser:
            self.browser.close()
