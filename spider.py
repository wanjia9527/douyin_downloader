import time
import requests
import json
import os
import threading
from playwright.sync_api import sync_playwright

# Configuration
SERVER_URL = "http://127.0.0.1:5000/push_videos"

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
        if '/aweme/v1/web/tab/feed/' in url or '/aweme/v1/web/aweme/post/' in url:
            try:
                data = response.json()
                process_and_send(data)
            except: pass
    except: pass

def process_and_send(data):
    """Extract and send video info."""
    aweme_list = data.get('aweme_list', [])
    if not aweme_list: return

    videos = []
    # Check if we are on the main feed (no specific author context usually implies feed)
    # But simpler: we let the batch_folder logic decide below.
    
    for item in aweme_list:
        video_obj = item.get('video', {})
        play_addr = video_obj.get('play_addr', {})
        url_list = play_addr.get('url_list', [])
        
        if url_list:
            videos.append({
                'id': item.get('aweme_id'),
                'title': item.get('desc', 'Untitled'),
                'url': url_list[-1],
                'author': item.get('author', {}).get('nickname', 'Unknown_Author')
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
                print(f"[+] Synced {res.json().get('added', 0)} videos to [{batch_folder}].")
        except Exception as e:
            print(f"[!] Sync error: {e}")

def run_spider(target_url):
    print(f"[*] Spider started using {BROWSER_TYPE}.")
    print(f"[*] Target: {target_url}")
    
    # 1. Get cookies explicitly
    cookies = get_cookies()

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 2. Inject cookies
        if cookies:
            context.add_cookies(cookies)
        
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page.on("response", intercept_response)

        print("[*] Navigating...")
        page.goto(target_url, timeout=60000)
        
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

            while True:
                try:
                    # Method 1: Mouse Wheel (More human-like)
                    page.mouse.wheel(0, 1000)
                    
                    # Method 2: Pressing Arrow Down explicitly
                    page.keyboard.press("ArrowDown")
                    
                    time.sleep(2)  # Wait for content load
                    print(".", end="", flush=True)
                except Exception:
                    break
        except KeyboardInterrupt:
            print("\n[*] Stopped.")
        
        try: browser.close()
        except: pass

if __name__ == "__main__":
    import sys
    # Default to Chrome
    BROWSER_TYPE = "chrome" 
    
    # If no URL provided, default to Homepage (Feed)
    if len(sys.argv) < 2:
        url = "https://www.douyin.com/"
        print("[*] No URL provided. Defaulting to Main Feed.")
    else:
        url = sys.argv[1]
    
    run_spider(url)
