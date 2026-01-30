import requests
import os
import re
import threading
import time
from queue import Queue
from flask import Flask, request, jsonify
from flask_cors import CORS
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Config
SAVE_DIR = "F:\douyin"  # Default download directory
PORT = 5000       
MAX_WORKERS = 16  

app = Flask(__name__)
CORS(app)

download_queue = Queue()
processing_ids = set()
downloaded_ids = set()
print_lock = threading.Lock()

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=MAX_WORKERS, 
    pool_maxsize=MAX_WORKERS,
    max_retries=Retry(total=3, backoff_factor=1)
)
session.mount('http://', adapter)
session.mount('https://', adapter)

def clean_filename(s):
    s = str(s).strip().replace(' ', '_')
    s = re.sub(r'(?u)[^-\w.]', '', s)
    return s[:60]

def log(msg):
    with print_lock:
        print(msg)

def downloader_worker(worker_id):
    while True:
        try:
            video_data = download_queue.get()
            if video_data is None: break
            
            url = video_data['url']
            title = video_data['title']
            aweme_id = video_data['id']
            
            # 拼接路径：根目录 + 子文件夹
            sub_folder = video_data.get('sub_folder', 'Default')
            target_dir = os.path.join(SAVE_DIR, sub_folder)
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                
            file_name = f"{clean_filename(title)}_{aweme_id}.mp4"
            file_path = os.path.join(target_dir, file_name)

            if os.path.exists(file_path):
                downloaded_ids.add(aweme_id)
                if aweme_id in processing_ids: processing_ids.remove(aweme_id)
                download_queue.task_done()
                continue
            
            # ... (后续下载逻辑保持不变，只需确保 indent 正确)
            log(f"[*] Downloading: {title[:25]}...")
            
            try:
                start_time = time.time()
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.douyin.com/'
                }
                
                resp = session.get(url, headers=headers, stream=True, timeout=30)
                
                if resp.status_code in [200, 206]:
                    with open(file_path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=1024*1024):
                            if chunk: f.write(chunk)
                    
                    elapsed = time.time() - start_time
                    size_mb = os.path.getsize(file_path) / 1024 / 1024
                    speed = size_mb / elapsed
                    log(f"[OK] {title[:25]}... ({size_mb:.1f}MB | {speed:.1f}MB/s)")
                    downloaded_ids.add(aweme_id)
                else:
                    log(f"[FAIL] {title[:25]}... HTTP {resp.status_code}")
            
            except Exception as e:
                log(f"[ERR] {title[:25]}... : {e}")
            finally:
                if aweme_id in processing_ids:
                    processing_ids.remove(aweme_id)
            
            download_queue.task_done()
        except Exception as e:
            log(f"[ERROR] Worker {worker_id} exception: {e}")

@app.route('/push_videos', methods=['POST'])
def receive_videos():
    try:
        data = request.json
        videos = data.get('videos', [])
        # 获取子文件夹名（例如：Douyin_Feed 或 作者名）
        # 如果是油猴脚本未传参，则默认存入 "Default_Downloads"
        sub_folder_name = data.get('folder', 'Default_Downloads')
        
        added_count = 0
        
        for v in videos:
            vid = v.get('id')
            if vid and vid not in downloaded_ids and vid not in processing_ids:
                # 明确标记这个字段叫 sub_folder
                v['sub_folder'] = sub_folder_name
                download_queue.put(v)
                processing_ids.add(vid) 
                added_count += 1
        
        q_size = download_queue.qsize()
        if added_count > 0:
            log(f"-> Added {added_count} tasks | Queue: {q_size}")
        
        return jsonify({"status": "success", "added": added_count, "queue_size": q_size})
    except Exception as e:
        log(f"[ERROR] API Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print(f"Server started on port {PORT} with {MAX_WORKERS} workers")
    
    for i in range(MAX_WORKERS):
        t = threading.Thread(target=downloader_worker, args=(i+1,), daemon=True)
        t.start()
    
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)