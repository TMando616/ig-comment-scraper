import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any
from datetime import datetime

class SpreadsheetManager:
    """
    Googleスプレッドシートの読み書きを管理するクラス
    """
    def __init__(self, spreadsheet_key: str, service_account_file: str):
        self.scopes: List[str] = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.credentials = Credentials.from_service_account_file(
            service_account_file,
            scopes=self.scopes
        )
        self.client = gspread.authorize(self.credentials)
        self.spreadsheet = self.client.open_by_key(spreadsheet_key)
        
        # シートの取得（存在しない場合はエラーになるため、事前に名前を確認することを推奨）
        try:
            self.target_sheet = self.spreadsheet.worksheet("ターゲット")
            self.result_sheet = self.spreadsheet.worksheet("出力結果")
        except gspread.exceptions.WorksheetNotFound:
            print("エラー: 'ターゲット' または '出力結果' シートが見つかりません。")
            raise

    def get_target_user_ids(self) -> List[str]:
        """
        「ターゲット」シートのA列からユーザーIDのリストを取得する（ヘッダーを除く）
        """
        try:
            # A列（1列目）の値をすべて取得し、1行目（ヘッダー）を除外
            values = self.target_sheet.col_values(1)
            return values[1:] if len(values) > 1 else []
        except Exception as e:
            print(f"ターゲットユーザーIDの取得中にエラーが発生しました: {e}")
            return []

    def append_results(self, rows: List[List[Any]]) -> bool:
        """
        「出力結果」シートに複数の結果を一括で追記する
        rowのフォーマット: [取得日時, ターゲットID, 投稿URL, コメントユーザーID, ユーザーURL, アカウント状態, フォロワー数, フォロー数, ステータス]
        """
        try:
            if not rows:
                return True
            self.result_sheet.append_rows(rows)
            return True
        except Exception as e:
            print(f"複数行の結果追記中にエラーが発生しました: {e}")
            return False

    def append_result(self, user_id: str, post_url: str, commenter_id: Any, commenter_url: str, account_status: str, followers: int, following: int, status: str) -> bool:
        """
        「出力結果」シートに1行の結果を追記する
        フォーマット: [取得日時, ターゲットユーザーID, 投稿URL, コメントユーザーID, ユーザーURL, アカウント状態, フォロワー数, フォロー数, ステータス]
        """
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [now, user_id, post_url, commenter_id, commenter_url, account_status, followers, following, status]
            self.result_sheet.append_row(row)
            return True
        except Exception as e:
            print(f"結果の追記中にエラーが発生しました ({user_id}): {e}")
            return False
