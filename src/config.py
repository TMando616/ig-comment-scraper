import os
from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()

class Config:
    """
    アプリケーション全体の設定・定数を管理するクラス
    """
    # --- Instagram 認証情報 ---
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
    STATE_FILE = os.getenv("STATE_FILE", "state.json")

    # --- Google Sheets 認証情報 ---
    SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY")
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    TARGET_SHEET_NAME = os.getenv("TARGET_SHEET_NAME", "ターゲット")
    RESULT_SHEET_NAME = os.getenv("RESULT_SHEET_NAME", "出力結果")

    # --- スクレイピング設定 ---
    DEFAULT_TARGET_POST_COUNT = int(os.getenv("DEFAULT_TARGET_POST_COUNT", "3"))
    MAX_RECENT_POSTS = 10
    
    # 待機時間（秒）
    WAIT_TIME_SHORT = (1, 2)
    WAIT_TIME_MEDIUM = (2, 5)
    WAIT_TIME_LONG = (3, 7)
    LOGIN_WAIT_TIMEOUT = 60000 # ミリ秒
    
    # --- ロギング設定 ---
    LOG_DIR = "logs"
    LOG_FILE = os.path.join(LOG_DIR, "app.log")
    LOG_FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
    
    # --- デバッグ設定 ---
    DEBUG_DIR = os.getenv("DEBUG_DIR", "debug")
    TRACE_FILE = os.path.join(DEBUG_DIR, "trace.zip")

    @classmethod
    def validate(cls):
        """必須設定のチェック"""
        missing = []
        if not cls.INSTAGRAM_USERNAME: missing.append("INSTAGRAM_USERNAME")
        if not cls.INSTAGRAM_PASSWORD: missing.append("INSTAGRAM_PASSWORD")
        if not cls.SPREADSHEET_KEY: missing.append("SPREADSHEET_KEY")
        if not cls.GOOGLE_SERVICE_ACCOUNT_FILE: missing.append("GOOGLE_SERVICE_ACCOUNT_FILE")
        
        if missing:
            raise ValueError(f"以下の環境変数が設定されていません: {', '.join(missing)}")
