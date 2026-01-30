import requests
from datetime import datetime
import os
import re
import threading
import shutil
import time
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify
from flask_cors import CORS
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# 从统一配置文件导入
from config import (
    SAVE_DIR, PORT, MAX_WORKERS, MIN_SEGMENT_SIZE, MAX_RETRIES,
    MAX_DOWNLOADS, MAX_QUEUE_SIZE, calc_segments, USER_AGENT
)

app = Flask(__name__)
CORS(app)

download_queue = Queue()
processing_ids = set()
downloaded_ids = set()
download_count = 0
print_lock = threading.Lock()

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# 为分片下载创建更大的连接池
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=MAX_WORKERS * 16,
    pool_maxsize=MAX_WORKERS * 16,
    max_retries=Retry(total=3, backoff_factor=0.5)
)
session.mount('http://', adapter)
session.mount('https://', adapter)

DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Referer': 'https://www.douyin.com/'
}

def clean_filename(s):
    s = str(s).strip().replace(' ', '_')
    s = re.sub(r'(?u)[^-\w.]', '', s)
    return s[:60]

def cleanup_leftover():
    """启动时清理上次残留的临时文件和分片文件夹"""
    cleaned = 0
    for root, dirs, files in os.walk(SAVE_DIR):
        # 清理 .parts 分片文件夹
        for d in dirs:
            if d.endswith('.parts'):
                path = os.path.join(root, d)
                try:
                    shutil.rmtree(path)
                    cleaned += 1
                except: pass
        # 清理 .downloading 临时文件
        for f in files:
            if f.endswith('.downloading'):
                path = os.path.join(root, f)
                try:
                    os.remove(path)
                    cleaned += 1
                except: pass
    if cleaned:
        print(f"  已清理 {cleaned} 个残留临时文件")

def log(msg):
    with print_lock:
        print(msg)


def download_segment(url, start, end, seg_path, seg_index, title_short):
    """下载单个分片，支持网络中断自动断点续传"""
    max_attempts = MAX_RETRIES + 6  # 增加遇到断开时的重试次数
    for attempt in range(1, max_attempts + 1):
        try:
            current_start = start
            if os.path.exists(seg_path):
                downloaded_size = os.path.getsize(seg_path)
                current_start = start + downloaded_size
                if current_start > end:
                    return True, seg_index, None
            else:
                downloaded_size = 0

            headers = {**DEFAULT_HEADERS, 'Range': f'bytes={current_start}-{end}'}
            resp = session.get(url, headers=headers, stream=True, timeout=(15, 120))

            if resp.status_code not in [200, 206]:
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
                return False, seg_index, f"HTTP {resp.status_code}"

            mode = 'ab' if resp.status_code == 206 and downloaded_size > 0 else 'wb'
            with open(seg_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        f.write(chunk)

            # 校验分片大小
            actual = os.path.getsize(seg_path) if os.path.exists(seg_path) else 0
            expected = end - start + 1
            if actual < expected:
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
                return False, seg_index, f"分片不完整 ({actual}/{expected})"

            return True, seg_index, None

        except Exception as e:
            if attempt < max_attempts:
                time.sleep(2)
                continue
            return False, seg_index, str(e)

    return False, seg_index, "重试耗尽"


def merge_segments(seg_paths, file_path):
    """合并所有分片为完整文件"""
    with open(file_path, 'wb') as out:
        for sp in seg_paths:
            with open(sp, 'rb') as seg:
                while True:
                    chunk = seg.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)


def cleanup_segments(seg_paths):
    """清理分片临时文件"""
    for sp in seg_paths:
        try:
            if os.path.exists(sp):
                os.remove(sp)
        except:
            pass


def get_file_size(url):
    """通过 HEAD 请求获取文件大小，并判断是否支持 Range 请求"""
    try:
        resp = session.head(url, headers=DEFAULT_HEADERS, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            content_length = resp.headers.get('Content-Length')
            accept_ranges = resp.headers.get('Accept-Ranges', '')
            supports_range = accept_ranges.lower() != 'none'
            total_size = int(content_length) if content_length else None
            return total_size, supports_range
    except:
        pass
    return None, False


def download_single_stream(url, file_path, temp_path, title_short):
    """单线程下载（回退方案），支持网络中断自动断点续传"""
    max_attempts = MAX_RETRIES + 6
    for attempt in range(1, max_attempts + 1):
        try:
            current_start = 0
            if os.path.exists(temp_path):
                current_start = os.path.getsize(temp_path)
                
            headers = {**DEFAULT_HEADERS}
            if current_start > 0:
                headers['Range'] = f'bytes={current_start}-'
                
            resp = session.get(url, headers=headers, stream=True, timeout=(15, 300))

            if resp.status_code not in [200, 206]:
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
                return False

            mode = 'ab' if resp.status_code == 206 and current_start > 0 else 'wb'
            with open(temp_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            actual_size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
            
            content_range = resp.headers.get('Content-Range')
            if content_range:
                try:
                    total_expected = int(content_range.split('/')[-1])
                    if actual_size < total_expected:
                        if attempt < max_attempts:
                            time.sleep(2)
                            continue
                        return False
                except: pass
            
            if actual_size < 10240:
                try: os.remove(temp_path)
                except: pass
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
                return False

            os.rename(temp_path, file_path)
            return True

        except Exception as e:
            if attempt < max_attempts:
                time.sleep(2)
                continue
            return False

    return False


def download_multi_segment(url, file_path, total_size, title_short):
    """多线程分片下载（类似IDM）"""

    # 根据文件大小动态计算分片数
    num_segments = calc_segments(total_size)

    if num_segments <= 1:
        # 文件太小，不值得分片，直接单线程下载
        temp_path = file_path + ".downloading"
        return download_single_stream(url, file_path, temp_path, title_short)

    # 计算每个分片的字节范围
    segment_size = total_size // num_segments
    ranges = []
    for i in range(num_segments):
        start = i * segment_size
        end = (i + 1) * segment_size - 1 if i < num_segments - 1 else total_size - 1
        ranges.append((start, end))

    seg_dir = file_path + ".parts"
    os.makedirs(seg_dir, exist_ok=True)
    seg_paths = [os.path.join(seg_dir, f"seg_{i:03d}") for i in range(num_segments)]

    log(f"  [▼] {title_short} | {total_size / 1024 / 1024:.1f}MB × {num_segments}分片")

    # 并行下载所有分片
    success = True
    with ThreadPoolExecutor(max_workers=num_segments) as executor:
        futures = {}
        for i, (start, end) in enumerate(ranges):
            f = executor.submit(download_segment, url, start, end, seg_paths[i], i, title_short)
            futures[f] = i

        for future in as_completed(futures):
            ok, seg_idx, err = future.result()
            if not ok:
                log(f"  [✗] {title_short} 分片 {seg_idx} 失败: {err}")
                success = False

    if not success:
        cleanup_segments(seg_paths)
        try: os.rmdir(seg_dir)
        except: pass
        return False

    # 合并分片
    try:
        merge_segments(seg_paths, file_path)
    except Exception as e:
        log(f"  [✗] {title_short} 合并失败: {e}")
        try: os.remove(file_path)
        except: pass
        cleanup_segments(seg_paths)
        try: os.rmdir(seg_dir)
        except: pass
        return False

    # 校验最终文件大小
    final_size = os.path.getsize(file_path)
    if final_size != total_size:
        log(f"  [✗] {title_short} 大小不匹配 ({final_size}/{total_size})")
        try: os.remove(file_path)
        except: pass
        cleanup_segments(seg_paths)
        try: os.rmdir(seg_dir)
        except: pass
        return False

    # 成功，清理分片
    cleanup_segments(seg_paths)
    try: os.rmdir(seg_dir)
    except: pass
    return True


def downloader_worker(worker_id):
    global download_count
    while True:
        try:
            video_data = download_queue.get()
            if video_data is None: break

            url = video_data['url']
            title = video_data['title']
            aweme_id = video_data['id']
            author = video_data.get('author', '')
            create_time = video_data.get('create_time', 0)

            # 格式化发布时间
            if create_time:
                date_str = datetime.fromtimestamp(create_time).strftime('%Y%m%d')
            else:
                date_str = 'unknown'

            sub_folder = video_data.get('sub_folder', 'Default')
            target_dir = os.path.join(SAVE_DIR, sub_folder)

            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            # 文件名格式: 发布日期_作者_标题.mp4
            author_clean = clean_filename(author)
            title_clean = clean_filename(title)
            base_name = f"{date_str}_{author_clean}_{title_clean}"
            file_name = f"{base_name}.mp4"
            file_path = os.path.join(target_dir, file_name)

            # 处理文件名冲突：如果文件已存在但不是同一个视频，则加编号
            if os.path.exists(file_path) and aweme_id not in downloaded_ids:
                counter = 2
                while os.path.exists(file_path):
                    file_name = f"{base_name}_{counter}.mp4"
                    file_path = os.path.join(target_dir, file_name)
                    counter += 1

            if os.path.exists(file_path):
                downloaded_ids.add(aweme_id)
                if aweme_id in processing_ids: processing_ids.remove(aweme_id)
                download_queue.task_done()
                continue

            title_short = title[:25]
            log(f"[↓] W{worker_id} | {title_short}")

            start_time = time.time()
            success = False

            # 1. 探测文件大小和 Range 支持
            total_size, supports_range = get_file_size(url)

            if total_size and supports_range and calc_segments(total_size) > 1:
                # 多线程分片下载
                success = download_multi_segment(url, file_path, total_size, title_short)
            else:
                # 单线程下载（服务器不支持 Range 或文件太小）
                if not supports_range and total_size:
                    log(f"  [!] 不支持分片")
                temp_path = file_path + ".downloading"
                success = download_single_stream(url, file_path, temp_path, title_short)

            elapsed = time.time() - start_time

            if success:
                size_mb = os.path.getsize(file_path) / 1024 / 1024
                speed = size_mb / elapsed if elapsed > 0 else 0
                log(f"[✓] {title_short} ({size_mb:.1f}MB | {speed:.1f}MB/s)")
                downloaded_ids.add(aweme_id)
                download_count += 1
                if MAX_DOWNLOADS > 0 and download_count >= MAX_DOWNLOADS:
                    log(f"\n[★] 已达到最大下载数量 {MAX_DOWNLOADS}，停止接收新任务")
            else:
                log(f"[FAIL] {title_short}... 下载失败，已跳过")

            if aweme_id in processing_ids:
                processing_ids.remove(aweme_id)

            download_queue.task_done()
        except Exception as e:
            log(f"[ERROR] Worker {worker_id}: {e}")


@app.route('/push_videos', methods=['POST'])
def receive_videos():
    try:
        global download_count
        data = request.json
        videos = data.get('videos', [])
        sub_folder_name = data.get('folder', 'Default_Downloads')

        # 检查是否已达下载上限
        if MAX_DOWNLOADS > 0 and download_count >= MAX_DOWNLOADS:
            return jsonify({"status": "limit_reached", "added": 0, "downloaded": download_count})

        # 检查队列是否已满
        current_queue = download_queue.qsize()
        if MAX_QUEUE_SIZE > 0 and current_queue >= MAX_QUEUE_SIZE:
            log(f"[!] 队列已满 ({current_queue}/{MAX_QUEUE_SIZE})，丢弃 {len(videos)} 个新任务")
            return jsonify({"status": "queue_full", "added": 0, "queue_size": current_queue, "max_queue_size": MAX_QUEUE_SIZE})

        added_count = 0

        for v in videos:
            # 达到下载上限后不再添加
            if MAX_DOWNLOADS > 0 and (download_count + len(processing_ids)) >= MAX_DOWNLOADS:
                break
            # 达到队列上限后不再添加
            if MAX_QUEUE_SIZE > 0 and download_queue.qsize() >= MAX_QUEUE_SIZE:
                log(f"[!] 队列已满 ({MAX_QUEUE_SIZE})，剩余任务被丢弃")
                break
            vid = v.get('id')
            if vid and vid not in downloaded_ids and vid not in processing_ids:
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
    print(f"========================================")
    print(f"  抖音视频下载器 - 动态分片加速引擎")
    print(f"  同时下载: {MAX_WORKERS} 个视频")
    print(f"  下载上限: {MAX_DOWNLOADS if MAX_DOWNLOADS > 0 else '无限制'}")
    print(f"  队列上限: {MAX_QUEUE_SIZE if MAX_QUEUE_SIZE > 0 else '无限制'}")
    print(f"  保存目录: {SAVE_DIR}")
    print(f"========================================")

    cleanup_leftover()

    for i in range(MAX_WORKERS):
        t = threading.Thread(target=downloader_worker, args=(i+1,), daemon=True)
        t.start()

    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)