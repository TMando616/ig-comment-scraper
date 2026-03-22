import os
import time
import re
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional, Tuple

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
            
            if os.path.exists(self.state_file):
                print("既存のセッションを使用してログインを試みます...")
                self.context = self.browser.new_context(storage_state=self.state_file)
            else:
                print("新規ログインを開始します...")
                self.context = self.browser.new_context()

            page = self.context.new_page()
            page.goto("https://www.instagram.com/")

            if page.query_selector('input[name="username"]'):
                print("ログイン情報を入力中...")
                page.fill('input[name="username"]', self.username)
                page.fill('input[name="password"]', self.password)
                page.click('button[type="submit"]')
                
                page.wait_for_load_state("networkidle")
                time.sleep(5)

                self.context.storage_state(path=self.state_file)
                print("セッション情報を保存しました。")
            else:
                print("既にログイン状態です。")
            
            return True
        except Exception as e:
            print(f"ログイン処理中にエラーが発生しました: {e}")
            return False

    def get_latest_post_url(self, user_id: str) -> Tuple[Optional[str], str]:
        """
        指定されたユーザーIDのプロフィールから最新投稿のURLを取得する
        戻り値: (URL, ステータスメッセージ)
        """
        if not self.context:
            return None, "エラー: 未ログイン"

        page: Page = self.context.new_page()
        profile_url = f"https://www.instagram.com/{user_id}/"
        try:
            print(f"プロフィールにアクセス中: {profile_url}")
            response = page.goto(profile_url)
            
            # ユーザーが存在しない場合（404等）
            if response.status == 404:
                return None, "失敗: ユーザーが存在しません"
            
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # 投稿一覧から最初の /p/ または /reel/ を含むaタグを探す
            # Instagramのプロフィール画面の投稿セレクタは変更されやすいため、属性で柔軟に探す
            post_link = page.query_selector('a[href*="/p/"], a[href*="/reel/"]')
            
            if post_link:
                href = post_link.get_attribute("href")
                full_url = f"https://www.instagram.com{href}"
                print(f"最新投稿URLを取得しました: {full_url}")
                return full_url, "成功"
            else:
                # 投稿が0件、または非公開アカウントの場合
                if page.query_selector('text="このアカウントは非公開です"'):
                    return None, "失敗: 非公開アカウント"
                return None, "失敗: 投稿が見つかりません（0件の可能性）"

        except Exception as e:
            return None, f"失敗: プロフィール取得エラー ({str(e)})"
        finally:
            page.close()

    def get_comment_count(self, post_url: str) -> Tuple[Optional[int], str]:
        """
        指定された投稿URLからコメント数を取得する
        戻り値: (コメント数, ステータスメッセージ)
        """
        if not self.context:
            return None, "エラー: 未ログイン"

        page: Page = self.context.new_page()
        try:
            print(f"投稿にアクセス中: {post_url}")
            page.goto(post_url)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # メタタグからコメント数を取得
            meta_desc = page.get_attribute('meta[property="og:description"]', 'content')
            if meta_desc:
                match = re.search(r'(\d+)\s*件のコメント', meta_desc) or re.search(r'(\d+)\s*Comments', meta_desc)
                if match:
                    count = int(match.group(1))
                    return count, "成功"

            # メタタグにない場合（コメント0件や構造変更）
            # 明示的に「0」と判断できる材料がない場合は、要素を探す必要があるが、
            # ここではプロトタイプとして0または取得不能として扱う
            return 0, "成功（または取得不能により0と判定）"

        except Exception as e:
            return None, f"失敗: コメント取得エラー ({str(e)})"
        finally:
            page.close()

    def close(self):
        if self.browser:
            self.browser.close()
