import os
import time
import re
import random
import json
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional, Tuple
from config import Config
from logger import logger

class InstagramScraper:
    """
    Instagramのスクレイピングを担当するクラス（デバッグ機能付き）
    """
    def __init__(self, username: str, password: str, state_file: str = Config.STATE_FILE, debug_dir: str = Config.DEBUG_DIR):
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
        logger.debug(f"スクリーンショットを保存しました: {path}")

    def login(self, playwright) -> bool:
        """
        Instagramにログインする。state.jsonがあればそれを読み込み、ログイン済みか確認する。
        """
        try:
            # ブラウザの起動
            self.browser = playwright.chromium.launch(headless=True)
            
            # 1. state.jsonが存在するかチェックしてコンテキストを作成
            if os.path.exists(self.state_file):
                logger.info(f"セッションファイル '{self.state_file}' を読み込みます...")
                try:
                    # state.json を一度読み込んで内容を補正する
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    
                    # cookies 内の sameSite 属性をチェック・補正
                    if 'cookies' in state:
                        for cookie in state['cookies']:
                            ss = cookie.get('sameSite')
                            # Playwright は Strict, Lax, None のいずれかしか受け付けない
                            if ss not in ["Strict", "Lax", "None"]:
                                if not ss or ss.lower() in ["unspecified", "no_restriction", ""]:
                                    cookie['sameSite'] = "Lax"
                                elif ss.capitalize() in ["Strict", "Lax", "None"]:
                                    cookie['sameSite'] = ss.capitalize()
                                else:
                                    cookie['sameSite'] = "None"
                    
                    self.context = self.browser.new_context(storage_state=state)
                except Exception:
                    logger.warning("セッションファイルの読み込み・補正中にエラーが発生しました。新規コンテキストで続行します。", exc_info=True)
                    self.context = self.browser.new_context()
            else:
                logger.warning(f"セッションファイル '{self.state_file}' が見つかりません。新規コンテキストを作成します。")
                self.context = self.browser.new_context()

            # トレースの開始
            self.context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page = self.context.new_page()
            logger.info("ログイン状態を確認するために Instagram トップページにアクセス中...")
            page.goto("https://www.instagram.com/")
            
            # 2. ログイン済みかどうかの判定
            try:
                page.wait_for_selector('svg[aria-label="ホーム"], svg[aria-label="Home"], svg[aria-label="検索"], svg[aria-label="Search"]', timeout=15000)
                logger.info("ログイン済みであることが確認できました。ログイン処理をスキップします。")
                self._take_screenshot(page, "login_skipped_already_logged_in")
                return True
            except Exception:
                logger.info("ログイン状態が確認できませんでした。ログインを試行します。")

            # 3. ログイン画面の入力欄が表示されるか確認
            try:
                page.wait_for_selector('input[name="username"], input[name="email"]', state='visible', timeout=10000)
            except Exception:
                logger.error("ログイン画面の入力欄が見つかりません。アクセス制限の可能性があります。")
                self._take_screenshot(page, "login_failed_no_input_found")
                return False

            time.sleep(random.uniform(*Config.WAIT_TIME_SHORT))

            # 4. ログイン情報の入力
            logger.info(f"ユーザーID: {self.username} でログインを試みます...")
            
            username_field = page.locator('input[name="username"], input[name="email"]').first
            for char in self.username:
                username_field.type(char, delay=random.randint(100, 300))
            
            time.sleep(random.uniform(0.5, 1.5))
            
            password_field = page.locator('input[name="password"], input[name="pass"]').first
            for char in self.password:
                password_field.type(char, delay=random.randint(100, 300))

            self._take_screenshot(page, "login_input_completed")
            
            # 5. ログインボタンクリック
            time.sleep(random.uniform(*Config.WAIT_TIME_SHORT))
            login_button = page.locator('button[type="submit"], div[role="button"]').filter(has_text=re.compile(r"^(ログイン|Log in)$")).first
            
            logger.info("ログインボタンをクリックします。")
            login_button.click()
            
            # 6. ログイン完了の待機
            logger.info(f"ログイン遷移を待機中（最大 {Config.LOGIN_WAIT_TIMEOUT/1000} 秒）...")
            try:
                page.wait_for_selector('svg[aria-label="ホーム"], svg[aria-label="Home"]', timeout=Config.LOGIN_WAIT_TIMEOUT)
                
                time.sleep(3)
                popups = ["text='後で'", "text='Not Now'", "button:has-text('後で')", "button:has-text('Not Now')"]
                for selector in popups:
                    if page.locator(selector).is_visible():
                        page.click(selector)
                        time.sleep(1)

                self.context.storage_state(path=self.state_file)
                logger.info(f"ログインに成功し、新しいセッション情報を '{self.state_file}' に保存しました。")
                self._take_screenshot(page, "login_success_and_state_saved")
                return True
            except Exception:
                logger.error("ログイン後の画面遷移を確認できませんでした。")
                self._take_screenshot(page, "login_timeout_error")
                return False

        except Exception:
            logger.exception("ログイン処理中に重大なエラーが発生しました")
            return False

    def get_post_count(self, page: Page) -> int:
        """プロフィールページから総投稿数を取得する"""
        try:
            post_count_elem = page.query_selector('header li:first-child span')
            if not post_count_elem:
                post_count_elem = page.query_selector('span:has-text("投稿"), span:has-text("posts")')

            if post_count_elem:
                text = post_count_elem.inner_text()
                count_str = re.sub(r'[^\d]', '', text)
                if count_str:
                    return int(count_str)
            
            return 0
        except Exception:
            logger.warning("投稿数取得中にエラーが発生しました", exc_info=True)
            return 0

    def get_recent_post_urls(self, user_id: str, max_posts: int = Config.MAX_RECENT_POSTS) -> Tuple[list[str], int, str]:
        """最新の投稿URLリストと総投稿数を取得する"""
        if not self.context:
            return [], 0, "エラー: 未ログイン"

        page: Page = self.context.new_page()
        profile_url = f"https://www.instagram.com/{user_id}/"
        try:
            logger.info(f"プロフィールにアクセス中: {profile_url}")
            response = page.goto(profile_url)
            
            if response.status == 404:
                self._take_screenshot(page, f"error_404_{user_id}")
                return [], 0, "失敗: ユーザーが存在しません"
            
            page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(*Config.WAIT_TIME_MEDIUM))
            self._take_screenshot(page, f"step3_profile_{user_id}")

            total_posts = self.get_post_count(page)
            logger.info(f"総投稿数: {total_posts}")

            if page.query_selector('text="このアカウントは非公開です"') or page.query_selector('text="This account is private"'):
                return [], 0, "失敗: 非公開アカウント"

            post_links = page.query_selector_all('a[href*="/p/"], a[href*="/reel/"]')
            
            urls = []
            seen_hrefs = set()
            for link in post_links:
                href = link.get_attribute("href")
                if href and href not in seen_hrefs:
                    full_url = f"https://www.instagram.com{href}"
                    urls.append(full_url)
                    seen_hrefs.add(href)
                    if len(urls) >= max_posts:
                        break
            
            if urls:
                logger.info(f"最新の {len(urls)} 件の投稿URLを取得しました。")
                return urls, total_posts, "成功"
            else:
                return [], total_posts, "失敗: 投稿が見つかりません（0件の可能性）"

        except Exception:
            logger.exception(f"プロフィール取得エラー ({user_id})")
            return [], 0, "失敗: プロフィール取得エラー"
        finally:
            page.close()

    def get_commenting_users(self, post_url: str, target_user_id: str = "") -> Tuple[list[dict], str]:
        """指定された投稿URLから、コメントしているユーザーの情報を取得する"""
        if not self.context:
            return [], "エラー: 未ログイン"

        page: Page = self.context.new_page()
        try:
            logger.info(f"投稿にアクセス中: {post_url}")
            page.goto(post_url)
            page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(*Config.WAIT_TIME_LONG))
            
            post_id = post_url.split('/')[-2] if post_url.endswith('/') else post_url.split('/')[-1]
            self._take_screenshot(page, f"step4_post_{post_id}")

            # 1. スクロール領域の特定
            scroll_selector = 'div.x5yr21d.xw2csxc.x1odjw0f.x1n2onr6'
            scrollable_area = page.locator(scroll_selector)

            if scrollable_area.count() > 0:
                logger.info("コメントスクロール領域を確認しました。スクロールを開始します...")
                for i in range(5):
                    try:
                        scrollable_area.evaluate("el => el.scrollTop = el.scrollHeight")
                        page.wait_for_timeout(random.randint(1500, 2500))
                    except Exception:
                        logger.warning("スクロール中にエラーが発生しました", exc_info=True)
                        break
                self._take_screenshot(page, f"step5_post_scrolled_{post_id}")

            # 2. 投稿者のユーザーIDを取得
            author_elem = page.query_selector('header a[role="link"], article header a')
            page_author_id = author_elem.inner_text().strip() if author_elem else ""
            exclude_ids = {target_user_id.lower(), page_author_id.lower()}

            # 3. コメント抽出
            comment_containers = page.locator('ul.x1qjc9v5 > div, ul.x1qjc9v5 > li').all()
            comment_map = {}
            
            for container in comment_containers:
                try:
                    id_selector = 'span._ap3a._aaco._aacw._aacx._aad7._aade'
                    id_elem = container.locator(id_selector).first
                    if not id_elem.is_visible():
                        continue
                    
                    user_id = id_elem.inner_text().strip().split('\n')[0]
                    if not user_id or user_id.lower() in exclude_ids or len(user_id) <= 1:
                        continue
                    if not re.match(r'^[a-zA-Z0-9._]+$', user_id):
                        continue

                    text_elems = container.locator('span[dir="auto"]').all()
                    comment_text = ""
                    if len(text_elems) > 1:
                        comment_text = text_elems[1].inner_text().replace("\n", " ").strip()
                    
                    if user_id not in comment_map:
                        comment_map[user_id] = []
                    if comment_text:
                        comment_map[user_id].append(comment_text)
                except Exception:
                    continue

            result_list = []
            for uid, texts in comment_map.items():
                merged_text = " / ".join(texts) if texts else "（本文なし）"
                result_list.append({"user_id": uid, "comment_text": merged_text})

            logger.info(f"一意のコメントユーザーを {len(result_list)} 名取得しました。")
            return result_list, "成功"

        except Exception:
            logger.exception(f"コメントユーザー取得エラー ({post_url})")
            return [], "失敗: コメントユーザー取得エラー"
        finally:
            page.close()

    def _convert_stat_to_int(self, text: str) -> int:
        """統計テキストを数値に変換する"""
        if not text:
            return 0
        clean_text = text.replace(',', '').strip().lower()
        try:
            if 'k' in clean_text:
                return int(float(clean_text.replace('k', '')) * 1000)
            elif 'm' in clean_text:
                return int(float(clean_text.replace('m', '')) * 1000000)
            else:
                num_str = re.sub(r'[^\d.]', '', clean_text)
                return int(float(num_str)) if num_str else 0
        except (ValueError, TypeError):
            return 0

    def get_profile_info(self, user_id: str) -> Tuple[str, int, int, str]:
        """プロフィールの詳細情報を取得する"""
        if not self.context:
            return "判定不能（未ログイン）", 0, 0, ""

        page: Page = self.context.new_page()
        profile_url = f"https://www.instagram.com/{user_id}/"
        try:
            time.sleep(random.uniform(*Config.WAIT_TIME_MEDIUM))
            logger.info(f"プロフィール情報を確認中: {profile_url}")
            response = page.goto(profile_url)
            
            if response.status == 404:
                return "判定不能（404）", 0, 0, ""
            
            page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(*Config.WAIT_TIME_MEDIUM))
            
            is_private = False
            private_selectors = ['text="このアカウントは非公開です"', 'text="This account is private"', 'svg[aria-label="非公開"]', 'svg[aria-label="Private"]']
            for selector in private_selectors:
                if page.locator(selector).is_visible():
                    is_private = True
                    break
            account_status = "非公開" if is_private else "公開"

            followers_count = 0
            following_count = 0
            
            # フォロワー数
            for sel in ['a[href*="/followers/"] span', 'a[href*="/followers/"]', 'li:has-text("フォロワー") span', 'li:has-text("followers") span']:
                elem = page.locator(sel).first
                if elem.is_visible():
                    followers_count = self._convert_stat_to_int(elem.inner_text())
                    if followers_count > 0: break
            
            # フォロー数
            for sel in ['a[href*="/following/"] span', 'a[href*="/following/"]', 'li:has-text("フォロー中") span', 'li:has-text("following") span']:
                elem = page.locator(sel).first
                if elem.is_visible():
                    following_count = self._convert_stat_to_int(elem.inner_text())
                    if following_count > 0: break

            # Bio
            bio_text = ""
            for sel in ['header section div:has-text("プロフィール") + div span', 'header section div.x78zum5.x1q0g3np.xieb34t span[dir="auto"]', 'main header section > div:nth-child(3) span']:
                bio_elem = page.locator(sel).first
                if bio_elem.is_visible():
                    bio_text = bio_elem.inner_text().replace("\n", " / ").strip()
                    if bio_text: break

            logger.info(f"ユーザー {user_id}: {account_status}, フォロワー: {followers_count}, フォロー: {following_count}")
            return account_status, followers_count, following_count, bio_text

        except Exception:
            logger.exception(f"プロフィール詳細取得エラー ({user_id})")
            return "判定エラー", 0, 0, ""
        finally:
            page.close()

    def stop_tracing(self):
        """トレースを停止して保存する"""
        if self.context:
            self.context.tracing.stop(path=Config.TRACE_FILE)
            logger.info(f"トレースログを保存しました: {Config.TRACE_FILE}")

    def close(self):
        if self.browser:
            self.browser.close()
