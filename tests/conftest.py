import pytest
import os
import json

@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    """
    Playwrightのブラウザコンテキスト引数をカスタマイズし、
    state.json が存在する場合はセッション情報を読み込みます。
    """
    state_file = "state.json"
    if os.path.exists(state_file):
        try:
            print(f"\n[INFO] セッションファイル '{state_file}' を読み込みます...")
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # scraper.py と同様のクッキー補正ロジック
            if 'cookies' in state:
                corrected_count = 0
                for cookie in state['cookies']:
                    ss = cookie.get('sameSite')
                    if ss not in ["Strict", "Lax", "None"]:
                        if not ss or ss.lower() in ["unspecified", "no_restriction", ""]:
                            cookie['sameSite'] = "Lax" # デフォルトをLaxに設定
                            corrected_count += 1
                        elif ss.capitalize() in ["Strict", "Lax", "None"]:
                            cookie['sameSite'] = ss.capitalize()
                            corrected_count += 1
                        else:
                            cookie['sameSite'] = "None"
                            corrected_count += 1
                if corrected_count > 0:
                    print(f"[INFO] {corrected_count} 件のクッキーの sameSite 属性を補正しました。")
            
            return {
                **browser_context_args,
                "storage_state": state,
            }
        except Exception as e:
            print(f"[ERROR] セッションファイルの読み込み・補正中にエラーが発生しました: {e}")
            print("[INFO] 新規コンテキストで続行します。")
    else:
        print(f"\n[WARN] セッションファイル '{state_file}' が見つかりません。新規コンテキストを使用します。")
    
    return browser_context_args
