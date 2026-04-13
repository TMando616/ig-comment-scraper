import pytest
from scraper import InstagramScraper

def test_convert_stat_to_int():
    """
    Instagramの統計テキスト（"1.2k", "1,500"等）を数値(int)に変換するメソッドをテストします。
    """
    scraper = InstagramScraper("dummy", "dummy")
    
    # 基本的な数値
    assert scraper._convert_stat_to_int("123") == 123
    assert scraper._convert_stat_to_int("1,234") == 1234
    
    # 'k' (1,000倍)
    assert scraper._convert_stat_to_int("1.2k") == 1200
    assert scraper._convert_stat_to_int("10k") == 10000
    
    # 'm' (1,000,000倍)
    assert scraper._convert_stat_to_int("1.5m") == 1500000
    
    # 日本語混じり
    assert scraper._convert_stat_to_int("1,234 投稿") == 1234
    assert scraper._convert_stat_to_int("123件") == 123
    
    # 無効な値や空文字
    assert scraper._convert_stat_to_int("") == 0
    assert scraper._convert_stat_to_int(None) == 0
    assert scraper._convert_stat_to_int("abc") == 0

def test_scraper_init():
    """
    InstagramScraperの初期化をテストします。
    """
    scraper = InstagramScraper("test_user", "test_pass", state_file="test_state.json", debug_dir="test_debug")
    assert scraper.username == "test_user"
    assert scraper.password == "test_pass"
    assert scraper.state_file == "test_state.json"
    assert scraper.debug_dir == "test_debug"
