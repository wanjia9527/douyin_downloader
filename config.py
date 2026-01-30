"""
统一配置模块 - 从 config.yaml 读取配置并导出为常量
"""
import os
import yaml

# 读取配置文件
_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

with open(_config_path, 'r', encoding='utf-8') as _f:
    _cfg = yaml.safe_load(_f)

# ========== 下载设置 ==========
SAVE_DIR = _cfg.get('save_dir', 'D:\\Douyin')
PORT = _cfg.get('port', 5000)
MAX_DOWNLOADS = _cfg.get('max_downloads', 0)  # 0 表示不限制
MAX_QUEUE_SIZE = _cfg.get('max_queue_size', 0)  # 0 表示不限制

# ========== 并发设置 ==========
MAX_WORKERS = _cfg.get('max_workers', 8)
MIN_SEGMENT_SIZE = _cfg.get('min_segment_size_mb', 2) * 1024 * 1024  # 转换为字节
MAX_RETRIES = _cfg.get('max_retries', 3)

# ========== 动态分片策略 ==========
_segment_rules = _cfg.get('segment_rules', [
    {'max_size_mb': 5, 'segments': 1},
    {'max_size_mb': 20, 'segments': 2},
    {'max_size_mb': 80, 'segments': 4},
    {'max_size_mb': 200, 'segments': 8},
    {'max_size_mb': 999999, 'segments': 16},
])

def calc_segments(file_size_bytes):
    """根据文件大小（字节）动态计算分片数量"""
    size_mb = file_size_bytes / (1024 * 1024)
    for rule in _segment_rules:
        if size_mb < rule['max_size_mb']:
            return rule['segments']
    return 16  # 默认最大分片数

# ========== 爬虫设置 ==========
SCROLL_INTERVAL = _cfg.get('scroll_interval', 2)
MAX_VIDEO_DURATION = _cfg.get('max_video_duration', 1200)
BROWSER_HEADLESS = _cfg.get('browser_headless', False)
TARGET_URL = _cfg.get('target_url', 'https://www.douyin.com/?recommend=1')

# ========== 标题过滤 ==========
_raw_black = _cfg.get('title_blacklist', []) or [] 
TITLE_BLACKLIST = [str(i) for i in _raw_black if i]

_raw_white = _cfg.get('title_whitelist', []) or []
TITLE_WHITELIST = [str(i) for i in _raw_white if i]

# ========== 请求头 ==========
USER_AGENT = _cfg.get('user_agent',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

# ========== 派生常量 ==========
SERVER_URL = f"http://127.0.0.1:{PORT}/push_videos"
