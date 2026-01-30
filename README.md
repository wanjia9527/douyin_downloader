# Douyin Downloader (Hybrid Edition)

Define your own way to download Douyin (TikTok China) videos. This project provides a high-performance **Downloader Core** (`main.py`) paired with two distinct operation modes.

## 🚀 Core Features
- **High Performance**: 16-32 concurrent threads with connection pooling.
- **Smart Pathing**: Videos are automatically organized into sub-folders (by Author or Source).
- **Deduping**: In-memory deduplication to prevent re-downloading videos in the same session.

---

## 🛠️ Preparation (Required for both modes)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure Storage**:
   Open `main.py` and set your preferred storage path:
   ```python
   SAVE_DIR = r"F:\Douyin_Videos"  # Change this to your path
   ```

3. **Start the Core Server**:
   You must keep this running for either mode to work.
   ```bash
   python main.py
   ```
   *Server listens on `http://127.0.0.1:5000`*

---

## 🎮 Mode A: Browser Assistant (Manual / Interactive)
*Best for: Browsing normally and downloading interesting videos as you see them.*

1. **Install UserScript**:
   - Install the [Tampermonkey](https://www.tampermonkey.net/) extension for Chrome/Edge.
   - Create a new script, copy content from `douyin_helper.user.js` and save.

2. **How to Use**:
   - Open [Douyin.com](https://www.douyin.com/) in your browser.
   - You will see a helper panel on the right.
   - **Just Browse**: As you scroll, the script automatically sniff video links and sends them to `main.py`.
   - **Auto-Scroll**: Click the "Start Auto-Scroll" button on the panel to let it scroll for you.
   - Videos will save to: `SAVE_DIR/Default_Downloads/`

---

## 🕷️ Mode B: Auto Spider (Fully Automated)
*Best for: Batch downloading a specific user's profile or building a local archive of the feed without opening a browser window.*

1. **Setup Cookies** (One-time setup):
   - Install **EditThisCookie** extension in your browser.
   - Login to Douyin.
   - Click extension icon -> **Export** (Arrow icon).
   - Paste the content into a file named `cookies.txt` in the project folder.

2. **How to Use**:
   - Keep `python main.py` running.
   - Open a **new terminal** and run:
     ```bash
     # To download Main Feed (Recommendations):
     python spider.py
     
     # To download a Specific User (Profile):
     python spider.py "https://www.douyin.com/user/USER_ID_URL"
     ```

3. **Behavior**:
   - An automated browser will open (using your cookies).
   - It will scroll automatically.
   - **Feed videos** save to: `SAVE_DIR/Douyin_Feed/`
   - **Profile videos** save to: `SAVE_DIR/Author_Name/`

---

## 📂 Project Structure
- `main.py`: **[Core]** The downloader server. Always run this first.
- `spider.py`: **[Mode B]** Automated Playwright spider.
- `douyin_helper.user.js`: **[Mode A]** Browser UserScript.
- `cookies.txt`: **[Mode B]** Auth file for the spider.
- `requirements.txt`: Python dependencies.

## 📝 License
MIT
