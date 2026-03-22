import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any

class SpreadsheetManager:
    """
    Googleスプレッドシートの読み書きを管理するクラス
    """
    def __init__(self, spreadsheet_key: str, service_account_file: str):
        # サービスアカウントのスコープ設定
        self.scopes: List[str] = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        # 認証情報の設定
        self.credentials = Credentials.from_service_account_file(
            service_account_file,
            scopes=self.scopes
        )
        # gspreadクライアントの初期化
        self.client = gspread.authorize(self.credentials)
        # スプレッドシートを開く
        self.spreadsheet = self.client.open_by_key(spreadsheet_key)
        self.worksheet = self.spreadsheet.get_worksheet(0)  # 最初のシートを使用

    def get_target_urls(self) -> List[Dict[str, Any]]:
        """
        スプレッドシートからターゲットURLのリストを取得する
        想定フォーマット: 1行目がヘッダー、A列にURL、B列にコメント数
        """
        try:
            # 全データを取得
            records = self.worksheet.get_all_records()
            # 行番号（1-indexed, ヘッダー込みなので+2）を付与して返す
            for i, record in enumerate(records):
                record['row_index'] = i + 2
            return records
        except Exception as e:
            print(f"スプレッドシートの読み込み中にエラーが発生しました: {e}")
            return []

    def update_comment_count(self, row_index: int, comment_count: int) -> bool:
        """
        指定した行のコメント数を更新する
        B列（2列目）を更新対象とする
        """
        try:
            self.worksheet.update_cell(row_index, 2, comment_count)
            return True
        except Exception as e:
            print(f"{row_index}行目の更新中にエラーが発生しました: {e}")
            return False
