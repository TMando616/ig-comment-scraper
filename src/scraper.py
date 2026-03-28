import os
import time
import re
import random
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional, Tuple

class InstagramScraper:
    """
    Instagramのスクレイピングを担当するクラス（デバッグ機能付き）
    """
    def __init__(self, username: str, password: str, state_file: str = "state.json", debug_dir: str = "debug"):
        self.username = username
        self.password = password
        self.state_file = state_file
        self.debug_dir = debug_dir
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # デバッグ用ディレクトリの作成
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)

    def _take_screenshot(self, page: Page, name: str):
        """スクリーンショットを保存する内部メソッド"""
        path = os.path.join(self.debug_dir, f"{name}.png")
        page.screenshot(path=path)
        print(f"スクリーンショットを保存しました: {path}")

    def login(self, playwright) -> bool:
        """
        Instagramにログインする。既存のセッションがあれば再利用する。
        Trace Viewer の開始処理を含む。
        """
        try:
            self.browser = playwright.chromium.launch(headless=True)
            
            if os.path.exists(self.state_file):
                print("既存のセッションを使用してログインを試みます...")
                self.context = self.browser.new_context(storage_state=self.state_file)
            else:
                print("新規ログインを開始します...")
                self.context = self.browser.new_context()

            # トレースの開始
            self.context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page = self.context.new_page()
            page.goto("https://www.instagram.com/")
            page.wait_for_load_state("networkidle")
            time.sleep(3)  # 画面が安定するまで待機
            time.sleep(random.uniform(3, 5))  # 画面が安定するまで待機

            # ログインが必要か判定（ユーザー名、メールアドレス、パスワード入力フィールドがあるか）
            user_input = page.query_selector('input[name="username"], input[name="email"]')
            pass_input = page.query_selector('input[name="password"]')
            
            if user_input and pass_input:
                print("ログイン情報を入力中...")
                user_input.fill(self.username)
                time.sleep(1)
                time.sleep(random.uniform(1, 2))
                pass_input.fill(self.password)
                time.sleep(2)  # 入力後の安定待ち
                time.sleep(random.uniform(2, 3))  # 入力後の安定待ち
                
                self._take_screenshot(page, "step1_login_input")
                page.click('button[type="submit"]')
                
                page.wait_for_load_state("networkidle")
                time.sleep(5)  # ログイン遷移待ち
                time.sleep(random.uniform(5, 7))  # ログイン遷移待ち

                self.context.storage_state(path=self.state_file)
                print("セッション情報を保存しました。")
            else:
                print("既にログイン状態です。")
            
            self._take_screenshot(page, "step2_after_login")
            return True
        except Exception as e:
            print(f"ログイン処理中にエラーが発生しました: {e}")
            return False

    def get_post_count(self, page: Page) -> int:
        """
        プロフィールページから総投稿数を取得する。
        pageオブジェクトは既にプロフィールページを開いていることを想定。
        """
        try:
            # 投稿数を含む要素を探す (例: "123 投稿" または "123 posts")
            # セレクタは変更されやすいため、正規表現でテキストから抽出を試みる
            post_count_elem = page.query_selector('header li:first-child span')
            if not post_count_elem:
                # 別のパターンを試行
                post_count_elem = page.query_selector('span:has-text("投稿"), span:has-text("posts")')

            if post_count_elem:
                text = post_count_elem.inner_text()
                # 数字以外の文字（カンマや「投稿」など）を除去して数値化
                count_str = re.sub(r'[^\d]', '', text)
                if count_str:
                    return int(count_str)
            
            return 0
        except Exception as e:
            print(f"投稿数取得中にエラーが発生しました: {e}")
            return 0

    def get_recent_post_urls(self, user_id: str, limit: int = 10) -> Tuple[list[str], int, str]:
        """
        指定されたユーザーIDのプロフィールから最新の投稿URLリスト（最大10件）と総投稿数を取得する
        """
        if not self.context:
            return [], 0, "エラー: 未ログイン"

        page: Page = self.context.new_page()
        profile_url = f"https://www.instagram.com/{user_id}/"
        try:
            print(f"プロフィールにアクセス中: {profile_url}")
            response = page.goto(profile_url)
            
            if response.status == 404:
                self._take_screenshot(page, f"error_404_{user_id}")
                return [], 0, "失敗: ユーザーが存在しません"
            
            page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(2, 4))
            self._take_screenshot(page, f"step3_profile_{user_id}")

            # 総投稿数を取得
            total_posts = self.get_post_count(page)
            print(f"総投稿数: {total_posts}")

            if page.query_selector('text="このアカウントは非公開です"'):
                return [], 0, "失敗: 非公開アカウント"

            # 投稿URLを収集
            # /p/ (通常投稿) または /reel/ (リール) のリンクを取得
            post_links = page.query_selector_all('a[href*="/p/"], a[href*="/reel/"]')
            
            urls = []
            seen_hrefs = set()
            for link in post_links:
                href = link.get_attribute("href")
                if href and href not in seen_hrefs:
                    full_url = f"https://www.instagram.com{href}"
                    urls.append(full_url)
                    seen_hrefs.add(href)
                    if len(urls) >= limit:
                        break
            
            if urls:
                print(f"{len(urls)} 件の投稿URLを取得しました。")
                return urls, total_posts, "成功"
            else:
                return [], total_posts, "失敗: 投稿が見つかりません（0件の可能性）"

        except Exception as e:
            return [], 0, f"失敗: プロフィール取得エラー ({str(e)})"
        finally:
            page.close()

    def get_latest_post_url(self, user_id: str) -> Tuple[Optional[str], str]:
        """
        指定されたユーザーIDのプロフィールから最新投稿のURLを取得する
        """
        if not self.context:
            return None, "エラー: 未ログイン"

        page: Page = self.context.new_page()
        profile_url = f"https://www.instagram.com/{user_id}/"
        try:
            print(f"プロフィールにアクセス中: {profile_url}")
            response = page.goto(profile_url)
            
            if response.status == 404:
                self._take_screenshot(page, f"error_404_{user_id}")
                return None, "失敗: ユーザーが存在しません"
            
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            time.sleep(random.uniform(2, 4))
            self._take_screenshot(page, f"step3_profile_{user_id}")

            post_link = page.query_selector('a[href*="/p/"], a[href*="/reel/"]')
            
            if post_link:
                href = post_link.get_attribute("href")
                full_url = f"https://www.instagram.com{href}"
                print(f"最新投稿URLを取得しました: {full_url}")
                return full_url, "成功"
            else:
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
        """
        if not self.context:
            return None, "エラー: 未ログイン"

        page: Page = self.context.new_page()
        try:
            print(f"投稿にアクセス中: {post_url}")
            page.goto(post_url)
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            time.sleep(random.uniform(2, 4))
            
            # URLからスラッグを抽出してファイル名に使用
            post_id = post_url.split('/')[-2] if post_url.endswith('/') else post_url.split('/')[-1]
            self._take_screenshot(page, f"step4_post_{post_id}")

            meta_desc = page.get_attribute('meta[property="og:description"]', 'content')
            if meta_desc:
                match = re.search(r'(\d+)\s*件のコメント', meta_desc) or re.search(r'(\d+)\s*Comments', meta_desc)
                match = re.search(r'([\d,]+)\s*件のコメント', meta_desc) or re.search(r'([\d,]+)\s*Comments', meta_desc)
                if match:
                    count = int(match.group(1))
                    # カンマを除去してから整数に変換
                    count = int(match.group(1).replace(',', ''))
                    return count, "成功"

            return 0, "成功（または取得不能により0と判定）"

        except Exception as e:
            return None, f"失敗: コメント取得エラー ({str(e)})"
        finally:
            page.close()

    def stop_tracing(self):
        """トレースを停止して保存する"""
        if self.context:
            trace_path = os.path.join(self.debug_dir, "trace.zip")
            self.context.tracing.stop(path=trace_path)
            print(f"トレースログを保存しました: {trace_path}")

    def close(self):
        if self.browser:
            self.browser.close()
