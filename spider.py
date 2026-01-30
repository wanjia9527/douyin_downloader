import time
import requests
import json
import os
import threading
from playwright.sync_api import sync_playwright

# 从统一配置文件导入
from config import (
    SERVER_URL, SCROLL_INTERVAL, MAX_VIDEO_DURATION,
    BROWSER_HEADLESS, TARGET_URL, USER_AGENT,
    TITLE_BLACKLIST, TITLE_WHITELIST
)

def get_cookies():
    """Load cookies explicitly from cookies.txt (Netscape or JSON format)."""
    path = "cookies.txt"
    if not os.path.exists(path):
        # Fallback to cookies.json
        path = "cookies.json"
        if not os.path.exists(path):
            print(f"[!] No cookies found. Please save cookies to 'cookies.txt'.")
            return []
    
    cookies = []
    content = ""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        print(f"[!] Read error: {e}")
        return []

    # 1. Try parsing as JSON first
    try:
        if content.startswith('[') or content.startswith('{'):
            raw_cookies = json.loads(content)
            if not isinstance(raw_cookies, list): raw_cookies = [raw_cookies]
            
            for c in raw_cookies:
                exp = c.get('expirationDate')
                # Ensure float if exists
                if exp is not None:
                    try: exp = float(exp)
                    except: exp = None
                    
                cookie_dict = {
                    'name': c.get('name'),
                    'value': c.get('value'),
                    'domain': c.get('domain'),
                    'path': c.get('path'),
                    'secure': c.get('secure', False),
                    'httpOnly': c.get('httpOnly', False),
                    'sameSite': 'Lax'
                }
                if exp is not None:
                    cookie_dict['expires'] = exp
                
                cookies.append(cookie_dict)
            print(f"[*] Parsed as JSON. Loaded {len(cookies)} cookies.")
            return cookies
    except json.JSONDecodeError:
        pass # Not JSON, try Netscape

    # 2. Try parsing as Netscape
    try:
        lines = content.splitlines()
        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 7:
                expires = None
                try:
                    if parts[4] and parts[4] != '0':
                        expires = float(parts[4])
                except: pass

                cookie_dict = {
                    'name': parts[5],
                    'value': parts[6],
                    'domain': parts[0],
                    'path': parts[2],
                    'httpOnly': False,
                    'secure': parts[3].upper() == 'TRUE',
                    'sameSite': 'Lax'
                }
                if expires is not None:
                    cookie_dict['expires'] = expires
                
                cookies.append(cookie_dict)
        print(f"[*] Parsed as Netscape. Loaded {len(cookies)} cookies.")
    except Exception as e:
        print(f"[!] Parsing error: {e}")

    return cookies

def intercept_response(response):
    """Intercept network responses to find video data."""
    try:
        url = response.url
        # 抖音的 API 接口经常变动，如 /aweme/v1/web/tab/feed/, /aweme/v1/web/general/feed/ 等
        if '/aweme/v1/web/' in url or '/aweme/v1/' in url:
            try:
                # 尝试解析 JSON 并检查是否包含视频列表
                data = response.json()
                if 'aweme_list' in data:
                    process_and_send(data)
            except Exception as e:
                print(f"[!] Process Error: {e}")
    except Exception as outer_e:
        print(f"[!] Intercept Error: {outer_e}")

def process_and_send(data):
    """Extract and send video info."""
    aweme_list = data.get('aweme_list', [])
    if not aweme_list: return

    videos = []
    skipped = 0
    # Check if we are on the main feed (no specific author context usually implies feed)
    # But simpler: we let the batch_folder logic decide below.
    
    for item in aweme_list:
        video_obj = item.get('video', {})
        
        # 时长过滤（duration 单位为毫秒）
        if MAX_VIDEO_DURATION > 0:
            duration_ms = video_obj.get('duration', 0)
            duration_sec = duration_ms / 1000
            if duration_sec > MAX_VIDEO_DURATION:
                skipped += 1
                continue
        
        best_url = None
        chosen_info = ""
        bit_rate_list = video_obj.get('bit_rate', [])
        
        if bit_rate_list:
            # 按码率从高到低排序
            sorted_rates = sorted(bit_rate_list, key=lambda x: x.get('bit_rate', 0), reverse=True)
            
            # 不兼容的编码类型（H.265 / H.266 等）
            hevc_codecs = {'bytevc1', 'hevc', 'h265', 'bytevc2', 'vvc', 'h266'}
            
            # 第一优先：H.264 编码的最高码率
            for rate_info in sorted_rates:
                codec = str(rate_info.get('codec_type', '')).lower()
                # 如果 codec_type 字段不存在，看 gear_name 是否包含 265/hevc 标识
                gear = rate_info.get('gear_name', '')
                
                is_hevc = codec in hevc_codecs or '265' in gear or 'hevc' in gear.lower()
                
                if not is_hevc:
                    rate_play_addr = rate_info.get('play_addr', {})
                    rate_url_list = rate_play_addr.get('url_list', [])
                    if rate_url_list:
                        best_url = rate_url_list[-1]
                        bitrate_kbps = rate_info.get('bit_rate', 0) // 1000
                        chosen_info = f"H.264 {gear} ({bitrate_kbps}kbps)"
                        break
            
            # 没有 H.264？打印警告，尝试用 play_addr_h264 字段
            if not best_url:
                h264_addr = video_obj.get('play_addr_h264', {})
                h264_urls = h264_addr.get('url_list', [])
                if h264_urls:
                    best_url = h264_urls[-1]
                    chosen_info = "play_addr_h264 (回退)"
        
        # 最终回退：使用默认 play_addr
        if not best_url:
            play_addr = video_obj.get('play_addr', {})
            url_list = play_addr.get('url_list', [])
            if url_list:
                best_url = url_list[-1]
                chosen_info = "play_addr (默认)"
        
        if best_url:
            desc = item.get('desc', 'Untitled')

            # 标题黑名单过滤
            if TITLE_BLACKLIST and any(kw in desc for kw in TITLE_BLACKLIST):
                skipped += 1
                continue

            # 标题白名单过滤
            if TITLE_WHITELIST and not any(kw in desc for kw in TITLE_WHITELIST):
                skipped += 1
                continue

            videos.append({
                'id': item.get('aweme_id'),
                'title': desc,
                'url': best_url,
                'author': item.get('author', {}).get('nickname', 'Unknown_Author'),
                'create_time': item.get('create_time', 0)
            })
    
    if videos:
        try:
            # Logic: If downloading from Feed, putting each video in a separate author folder is messy.
            # We detect if the URL being scraped is the homepage, but here in process_and_send we only have data.
            # So we use a simple heuristic: if we are running in default mode (feed), we use a generic folder.
            
            # Since we can't easily pass the context down here without changing signatures, 
            # let's change how main is called or just use a fixed strategy.
            # Strategy: If user didn't specify a target URL (meaning Feed), use 'Douyin_Feed'.
            # If user specified a target URL (meaning Profile), use the author name.
            
            # Actually, let's just make it simpler:
            # If it's a mix of authors (feed), use "Douyin_Feed".
            # If all videos are from same author (profile), use that author name.
            
            authors = set(v['author'] for v in videos)
            if len(authors) > 1:
                batch_folder = "Douyin_Feed"
            else:
                batch_folder = videos[0]['author']

            payload = {'videos': videos, 'folder': batch_folder}
            res = requests.post(SERVER_URL, json=payload)
            if res.status_code == 200:
                added = res.json().get('added', 0)
                skip_info = f" (过滤{skipped}个)" if skipped else ""
                print(f"\n[+] 发送 {added} 个视频 → [{batch_folder}]{skip_info}")
        except Exception as e:
            print(f"[!] Sync error: {e}")

def run_spider(target_url):
    print(f"[*] Spider started.")
    print(f"[*] Target: {target_url}")
    
    # 1. Get cookies explicitly
    cookies = get_cookies()

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=BROWSER_HEADLESS, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent=USER_AGENT
        )
        
        # 2. Inject cookies
        if cookies:
            context.add_cookies(cookies)
        
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page.on("response", intercept_response)

        print("[*] Navigating...")
        page.goto(target_url, timeout=60000)
        
        # 检测是否被重定向到了其他页面（如 /jingxuan），如果是则尝试跳转回目标页
        current_url = page.url
        if 'recommend=1' in target_url and 'recommend=1' not in current_url:
            print(f"[!] 被重定向到了 {current_url}，正在尝试跳转回推荐页...")
            time.sleep(1)
            page.goto(target_url, timeout=60000)
            time.sleep(2)
            # 如果还是被重定向，就接受当前页面继续工作
            if 'recommend=1' not in page.url:
                print(f"[!] 仍被重定向到 {page.url}，将在当前页面继续抓取（不影响功能）")
        
        print(f"[*] 当前页面: {page.url}")
        
        # Wait for any video list container or just wait a bit
        try:
            page.wait_for_selector('div[data-e2e="feed-container"]', timeout=5000)
        except:
            print("[!] Warning: Feed container not found, blindly scrolling...")

        print("[*] Scrolling started. Press Ctrl+C to stop.")
        try:
            # Click the page to ensure focus
            try: page.mouse.click(100, 100)
            except: pass

            scroll_count = 0
            while True:
                try:
                    page.mouse.wheel(0, 1000)
                    page.keyboard.press("ArrowDown")
                    time.sleep(SCROLL_INTERVAL)
                    scroll_count += 1
                    if scroll_count % 3 == 0:
                        print(".", end="", flush=True)
                except Exception:
                    break
        except KeyboardInterrupt:
            print("\n[*] Stopped.")
        
        try: browser.close()
        except: pass

if __name__ == "__main__":
    import sys
    
    # If no URL provided, use config default
    if len(sys.argv) < 2:
        url = TARGET_URL
        print(f"[*] No URL provided. Using default: {url}")
    else:
        url = sys.argv[1]
    
    run_spider(url)
