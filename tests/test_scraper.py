import pytest
import os
import re
from playwright.sync_api import Page, expect

def test_instagram_title(page: Page):
    """
    Instagramのトップページにアクセスし、タイトルに 'Instagram' が含まれていることを確認します。
    """
    page.goto("https://www.instagram.com/")
    # タイトルに "Instagram" が含まれていることを確認
    expect(page).to_have_title(re.compile(r"Instagram"))

def test_login_state(page: Page):
    """
    state.json によりログイン画面がスキップされているか確認するテスト。
    ホームアイコンや検索アイコンが表示されていればログイン済みとみなす。
    """
    page.goto("https://www.instagram.com/")
    
    # CIなどで state.json が存在しない場合はテストをスキップする
    if not os.path.exists("state.json"):
        pytest.skip("state.json が見つからないため、ログイン状態のテストをスキップします。")
        
    try:
        # ログイン済みの場合に表示される要素（ホーム/検索/メッセージアイコンなど）を待機
        # aria-label が "ホーム" (日本語) または "Home" (英語) のものを検索
        page.wait_for_selector('svg[aria-label="ホーム"], svg[aria-label="Home"], svg[aria-label="検索"], svg[aria-label="Search"]', timeout=15000)
        assert True
    except Exception:
        pytest.fail("ログイン状態が確認できませんでした。state.json が無効であるか、アクセス制限の可能性があります。")
