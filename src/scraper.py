import os
import time
import re
import random
import json
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
        Instagramにログインする。state.jsonがあればそれを読み込み、ログイン済みか確認する。
        """
        try:
            # ブラウザの起動
            self.browser = playwright.chromium.launch(headless=True)
            
            # 1. state.jsonが存在するかチェックしてコンテキストを作成
            if os.path.exists(self.state_file):
                print(f"セッションファイル '{self.state_file}' を読み込みます...")
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
                                # 無効な値、空文字、または大文字小文字が異なる場合は修正
                                if not ss or ss.lower() in ["unspecified", "no_restriction", ""]:
                                    cookie['sameSite'] = "Lax" # デフォルトをLaxに設定
                                elif ss.capitalize() in ["Strict", "Lax", "None"]:
                                    cookie['sameSite'] = ss.capitalize()
                                else:
                                    cookie['sameSite'] = "None"
                    
                    self.context = self.browser.new_context(storage_state=state)
                except Exception as e:
                    print(f"セッションファイルの読み込み・補正中にエラーが発生しました: {e}")
                    print("新規コンテキストで続行します。")
                    self.context = self.browser.new_context()
            else:
                print(f"警告: セッションファイル '{self.state_file}' が見つかりません。新規コンテキストを作成します。")
                self.context = self.browser.new_context()

            # トレースの開始
            self.context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page = self.context.new_page()
            print("ログイン状態を確認するために Instagram トップページにアクセス中...")
            page.goto("https://www.instagram.com/")
            
            # 2. ログイン済みかどうかの判定（ホームアイコンやプロフィールアイコンの存在）
            try:
                # ホームアイコン、検索アイコン、またはメッセージアイコンのいずれかがあればログイン済みとみなす
                page.wait_for_selector('svg[aria-label="ホーム"], svg[aria-label="Home"], svg[aria-label="検索"], svg[aria-label="Search"]', timeout=15000)
                print("ログイン済みであることが確認できました。ログイン処理をスキップします。")
                self._take_screenshot(page, "login_skipped_already_logged_in")
                return True
            except Exception:
                print("ログイン状態が確認できませんでした。ログインを試行します。")

            # 3. ログイン画面の入力欄が表示されるか確認
            try:
                # ユーザー名入力欄が表示されるまで待機
                page.wait_for_selector('input[name="username"], input[name="email"]', state='visible', timeout=10000)
            except Exception:
                print("ログイン画面の入力欄が見つかりません。アクセス制限の可能性があります。")
                self._take_screenshot(page, "login_failed_no_input_found")
                return False

            time.sleep(random.uniform(1, 2))

            # 4. ログイン情報の入力（state.jsonが無効な場合のフォールバック）
            print(f"ユーザーID: {self.username} でログインを試みます...")
            
            # ユーザー名入力 (username または email)
            username_field = page.locator('input[name="username"], input[name="email"]').first
            for char in self.username:
                username_field.type(char, delay=random.randint(100, 300))
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # パスワード入力 (password または pass)
            password_field = page.locator('input[name="password"], input[name="pass"]').first
            for char in self.password:
                password_field.type(char, delay=random.randint(100, 300))

            self._take_screenshot(page, "login_input_completed")
            
            # 5. ログインボタンクリック
            time.sleep(random.uniform(1, 2))
            login_button = page.locator('button[type="submit"], div[role="button"]').filter(has_text=re.compile(r"^(ログイン|Log in)$")).first
            
            print("ログインボタンをクリックします。")
            login_button.click()
            
            # 6. ログイン完了の待機（待機時間を長めに設定）
            print("ログイン遷移を待機中（最大60秒）...")
            try:
                page.wait_for_selector('svg[aria-label="ホーム"], svg[aria-label="Home"]', timeout=60000)
                
                # ログイン成功後に邪魔なポップアップがあれば閉じる（「情報を保存」など）
                time.sleep(3)
                popups = ["text='後で'", "text='Not Now'", "button:has-text('後で')", "button:has-text('Not Now')"]
                for selector in popups:
                    if page.locator(selector).is_visible():
                        page.click(selector)
                        time.sleep(1)

                # 新しいセッションを保存
                self.context.storage_state(path=self.state_file)
                print(f"ログインに成功し、新しいセッション情報を '{self.state_file}' に保存しました。")
                self._take_screenshot(page, "login_success_and_state_saved")
                return True
            except Exception:
                print("ログイン後の画面遷移を確認できませんでした。")
                self._take_screenshot(page, "login_timeout_error")
                return False

        except Exception as e:
            print(f"ログイン処理中に重大なエラーが発生しました: {e}")
            return False

        except Exception as e:
            print(f"ログイン処理中にエラーが発生しました: {e}")
            self._take_screenshot(page, "error_login_failed")
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

    def get_recent_post_urls(self, user_id: str, max_posts: int = 10) -> Tuple[list[str], int, str]:
        """
        指定されたユーザーIDのプロフィールから最新の投稿URLリスト（最大 max_posts 件）と総投稿数を取得する
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
                    if len(urls) >= max_posts:
                        break
            
            if urls:
                print(f"最新の {len(urls)} 件の投稿URLを取得しました。")
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

    def get_commenting_users(self, post_url: str, target_user_id: str = "") -> Tuple[list[dict], str]:
        """
        指定された投稿URLから、コメントしているユーザーのIDとコメント内容のリストを取得する。
        """
        if not self.context:
            return [], "エラー: 未ログイン"

        page: Page = self.context.new_page()
        try:
            print(f"投稿にアクセス中: {post_url}")
            page.goto(post_url)
            page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(3, 5))
            
            # URLからスラッグを抽出してデバッグ用に使用
            post_id = post_url.split('/')[-2] if post_url.endswith('/') else post_url.split('/')[-1]
            self._take_screenshot(page, f"step4_post_{post_id}")

            # 1. スクロール領域（div要素）を特定
            scroll_selector = 'div.x5yr21d.xw2csxc.x1odjw0f.x1n2onr6'
            scrollable_area = page.locator(scroll_selector)

            if scrollable_area.count() > 0:
                print("コメントスクロール領域を確認しました。スクロールを開始します...")
                for i in range(5):
                    try:
                        scrollable_area.evaluate("el => el.scrollTop = el.scrollHeight")
                        page.wait_for_timeout(random.randint(1500, 2500))
                    except Exception as scroll_error:
                        print(f"スクロール中にエラーが発生しました: {scroll_error}")
                        break
                self._take_screenshot(page, f"step5_post_scrolled_{post_id}")

            # 2. 投稿者のユーザーIDを取得（除外対象の特定）
            author_elem = page.query_selector('header a[role="link"], article header a')
            page_author_id = author_elem.inner_text().strip() if author_elem else ""
            exclude_ids = {target_user_id.lower(), page_author_id.lower()}

            # 3. 各コメントのコンテナ要素をループ処理
            comment_containers = page.locator('ul.x1qjc9v5 > div, ul.x1qjc9v5 > li').all()
            
            comment_map = {} # user_id -> comment_text_list
            
            for container in comment_containers:
                try:
                    # ユーザーIDの抽出
                    id_selector = 'span._ap3a._aaco._aacw._aacx._aad7._aade'
                    id_elem = container.locator(id_selector).first
                    if not id_elem.is_visible():
                        continue
                    
                    user_id = id_elem.inner_text().strip().split('\n')[0]
                    
                    # 基本チェック
                    if not user_id or user_id.lower() in exclude_ids or len(user_id) <= 1:
                        continue
                    if not re.match(r'^[a-zA-Z0-9._]+$', user_id):
                        continue

                    # コメント本文の抽出
                    text_elems = container.locator('span[dir="auto"]').all()
                    comment_text = ""
                    if len(text_elems) > 1:
                        comment_text = text_elems[1].inner_text().replace("\n", " ").strip()
                    
                    if user_id not in comment_map:
                        comment_map[user_id] = []
                    
                    if comment_text:
                        comment_map[user_id].append(comment_text)
                except Exception as e:
                    continue

            # 重複排除とデータ整形
            result_list = []
            for uid, texts in comment_map.items():
                merged_text = " / ".join(texts) if texts else "（本文なし）"
                result_list.append({
                    "user_id": uid,
                    "comment_text": merged_text
                })

            print(f"一意のコメントユーザーを {len(result_list)} 名取得しました。")
            return result_list, "成功"

        except Exception as e:
            return [], f"失敗: コメントユーザー取得エラー ({str(e)})"
        finally:
            page.close()

    def get_comment_count(self, post_url: str) -> Tuple[Optional[int], str]:
        """
        指定された投稿URLからコメント数を取得する。
        「コメント...件をすべて見る」ボタンのテキストから数値を抽出。
        """
        if not self.context:
            return None, "エラー: 未ログイン"

        page: Page = self.context.new_page()
        try:
            print(f"投稿にアクセス中: {post_url}")
            page.goto(post_url)
            page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(3, 5))
            
            # URLからスラッグを抽出してファイル名に使用
            post_id = post_url.split('/')[-2] if post_url.endswith('/') else post_url.split('/')[-1]
            self._take_screenshot(page, f"step4_post_{post_id}")

            # 1. 指定されたセレクタで2番目の要素を特定
            comment_buttons = page.locator('span[role="button"].x1ypdohk, span[role="button"].x1s688f')
            
            # 2. テキストの抽出と数値化
            count = 0
            # 「いいね」ボタンと重複するため、2番目（index: 1）をターゲットにする
            if comment_buttons.count() > 1:
                target_button = comment_buttons.nth(1)
                text = target_button.inner_text()
                print(f"コメントボタン（2番目）のテキスト: {text}")
                
                # 正規表現で数値を抽出
                match = re.search(r'([\d,]+)', text)
                if match:
                    count_str = match.group(1).replace(',', '')
                    count = int(count_str)
                    print(f"抽出されたコメント数: {count}")
            else:
                print(f"十分な数のコメントボタンが見つかりません（取得数: {comment_buttons.count()}）。")
                
                # フォールバック: ボタンが1つしかない場合、それが目的の要素である可能性を試す
                if comment_buttons.count() == 1:
                    text = comment_buttons.first.inner_text()
                    match = re.search(r'([\d,]+)', text)
                    if match:
                        count = int(match.group(1).replace(',', ''))
                        print(f"最初のボタンから抽出されたコメント数: {count}")

                # 最終的な保険としてメタデータからも抽出
                if count == 0:
                    meta_desc = page.get_attribute('meta[property="og:description"]', 'content')
                    if meta_desc:
                        match = re.search(r'([\d,]+)\s*(件のコメント|Comments)', meta_desc)
                        if match:
                            count = int(match.group(1).replace(',', ''))
                            print(f"メタデータから抽出されたコメント数: {count}")

            return count, "成功"

        except Exception as e:
            print(f"コメント数取得中にエラーが発生しました（0として扱います）: {e}")
            return 0, f"警告: 取得エラー ({str(e)})"
        finally:
            page.close()

    def _convert_stat_to_int(self, text: str) -> int:
        """
        Instagramの統計テキスト（"1.2k", "1,500"等）を数値(int)に変換する。
        """
        if not text:
            return 0
        
        # カンマを除去
        clean_text = text.replace(',', '').strip().lower()
        
        try:
            if 'k' in clean_text:
                return int(float(clean_text.replace('k', '')) * 1000)
            elif 'm' in clean_text:
                return int(float(clean_text.replace('m', '')) * 1000000)
            else:
                # 数字以外の文字（「件」など）を除去して数値化
                num_str = re.sub(r'[^\d.]', '', clean_text)
                return int(float(num_str)) if num_str else 0
        except (ValueError, TypeError):
            return 0

    def get_profile_info(self, user_id: str) -> Tuple[str, int, int, str]:
        """
        指定されたユーザーIDのプロフィールにアクセスし、
        非公開判定、フォロワー数、フォロー数、プロフィール文を一括で取得する。
        """
        if not self.context:
            return "判定不能（未ログイン）", 0, 0, ""

        page: Page = self.context.new_page()
        profile_url = f"https://www.instagram.com/{user_id}/"
        try:
            # Bot検知回避のためのランダム待機（遷移前）
            time.sleep(random.uniform(2, 5))
            
            print(f"プロフィール情報を確認中: {profile_url}")
            response = page.goto(profile_url)
            
            if response.status == 404:
                return "判定不能（404）", 0, 0, ""
            
            # ページ読み込み後のランダム待機（遷移後）
            page.wait_for_load_state("networkidle")
            time.sleep(random.uniform(2, 5))
            
            # 1. 非公開アカウントの判定
            is_private = False
            private_selectors = [
                'text="このアカウントは非公開です"',
                'text="This account is private"',
                'svg[aria-label="非公開"]',
                'svg[aria-label="Private"]'
            ]
            for selector in private_selectors:
                if page.locator(selector).is_visible():
                    is_private = True
                    break
            
            account_status = "非公開" if is_private else "公開"

            # 2. フォロワー数・フォロー数の取得
            followers_count = 0
            following_count = 0

            # フォロワー数の取得
            followers_selectors = [
                'a[href*="/followers/"] span',
                'a[href*="/followers/"]',
                'li:has-text("フォロワー") span',
                'li:has-text("followers") span'
            ]
            for sel in followers_selectors:
                elem = page.locator(sel).first
                if elem.is_visible():
                    followers_text = elem.inner_text()
                    followers_count = self._convert_stat_to_int(followers_text)
                    if followers_count > 0: break

            # フォロー数の取得
            following_selectors = [
                'a[href*="/following/"] span',
                'a[href*="/following/"]',
                'li:has-text("フォロー中") span',
                'li:has-text("following") span'
            ]
            for sel in following_selectors:
                elem = page.locator(sel).first
                if elem.is_visible():
                    following_text = elem.inner_text()
                    following_count = self._convert_stat_to_int(following_text)
                    if following_count > 0: break

            # 3. プロフィール文（Bio）の取得
            bio_text = ""
            # プロフィール文が含まれる一般的なセレクタ
            bio_selectors = [
                'header section div:has-text("プロフィール") + div span', # 日本語設定
                'header section div.x78zum5.x1q0g3np.xieb34t span[dir="auto"]',
                'main header section > div:nth-child(3) span'
            ]
            
            for sel in bio_selectors:
                bio_elem = page.locator(sel).first
                if bio_elem.is_visible():
                    raw_bio = bio_elem.inner_text()
                    # 改行を " / " に置換してスプレッドシートで見やすくする
                    bio_text = raw_bio.replace("\n", " / ").strip()
                    if bio_text: break

            print(f"ユーザー {user_id}: {account_status}, フォロワー: {followers_count}, フォロー: {following_count}, Bio: {bio_text[:30]}...")
            return account_status, followers_count, following_count, bio_text

        except Exception as e:
            print(f"プロフィール情報取得中にエラーが発生しました ({user_id}): {e}")
            return "判定エラー", 0, 0, ""
        finally:
            page.close()

    def is_private_account(self, user_id: str) -> str:
        """
        互換性のために残すメソッド。内部で get_profile_info を呼び出す。
        """
        status, _, _, _ = self.get_profile_info(user_id)
        return status

    def stop_tracing(self):
        """トレースを停止して保存する"""
        if self.context:
            trace_path = os.path.join(self.debug_dir, "trace.zip")
            self.context.tracing.stop(path=trace_path)
            print(f"トレースログを保存しました: {trace_path}")

    def close(self):
        if self.browser:
            self.browser.close()
