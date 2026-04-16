import os
import logging
from config import Config

def setup_logger(name: str = "ig_scraper") -> logging.Logger:
    """
    アプリケーション全体で使用するロガーを設定する。
    """
    # ログディレクトリの作成
    if not os.path.exists(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 既存のハンドラーをクリア（二重出力を防ぐ）
    if logger.hasHandlers():
        logger.handlers.clear()

    # フォーマッターの設定
    formatter = logging.Formatter(Config.LOG_FORMAT)

    # 1. 標準出力ハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. ファイル出力ハンドラー
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# デフォルトロガーのインスタンスを提供
logger = setup_logger()
