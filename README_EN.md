# Douyin Batch Downloader

[中文说明](README.md) | [English Version](README_EN.md)

[[Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[[License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[[GitHub stars](https://img.shields.io/github/stars/wanjia9527/douyin_downloader?style=for-the-badge)](https://github.com/wanjia9527/douyin_downloader/stargazers)

> **An efficient, dual‑mode high‑quality Douyin video downloader.**  
> Whether you want to download as you scroll (manual mode) or batch‑archive all videos from a creator (automatic mode), this tool fits your needs.

---

## ✨ Key Features

- **🚀 Blazing Fast** – Powered by `requests` connection pooling and multithreading (supports 16‑32 concurrent threads).
- **🛡️ Anti‑block Bypass** – Load local cookies (`cookies.txt`, Netscape format) to easily bypass login restrictions.
- **📁 Auto‑organize**:
  - Recommended feed → `SAVE_DIR/Douyin_Feed/`
  - User homepage → `SAVE_DIR/author_nickname/`
- **🎭 Dual Modes**:
  - **Browser assistant mode** – With a Tampermonkey script, auto‑capture videos while browsing.
  - **Fully automatic crawler mode** – Background scrolling and fetching.

---

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=wanjia9527/douyin_downloader&type=Date)](https://star-history.com/#wanjia9527/douyin_downloader&Date)

---

## 🛠️ Quick Start

### 1. Install

```bash
git clone https://github.com/wanjia9527/douyin_downloader.git
cd douyin_downloader
pip install -r requirements.txt
playwright install chromium
```

### 2. Set Save Directory

Open `config.py` and change `SAVE_DIR` (e.g.):
```python
SAVE_DIR = r"F:\Douyin_Videos"
```

### 3. Start Core Service
**Important: this service must be running for any mode to work.**
```bash
python main.py
```

---

## 📖 Usage Guide

### Mode A: Browser Assistant (Manual / Semi‑auto)
*Use when scrolling Douyin and you only want to download some videos.*

1. Install [Tampermonkey](https://www.tampermonkey.net/) in your browser.
2. Create a new script, paste the content of [`douyin_helper.user.js`](douyin_helper.user.js), and save.
3. Open [Douyin.com](https://www.douyin.com/). A floating panel will appear on the right.
4. **Start scrolling** – the script captures videos and sends them to the background downloader.

### Mode B: Fully Automatic Crawler (Batch Archive)
*Use to download all works from a creator without opening the browser, or to keep downloading the recommended feed.*

1. **Set up cookies (once)**:
   - Install the **EditThisCookie** browser extension.
   - Log in to Douyin web, click the extension icon, and **export** cookies.
   - Create a `cookies.txt` file in the project root and paste the exported content.
2. **Run the crawler**:
   ```bash
   # Download recommended feed (infinite mode)
   python spider.py

   # Download all videos from a specific user
   python spider.py "https://www.douyin.com/user/MS4wLjABAAAA..."
   ```

> **💡 Tips**:
> 1. Open `spider.py` and adjust `SCROLL_INTERVAL = 2` (seconds) to change scrolling speed.
> 2. The default URL is locked to the recommended feed (`/?recommend=1`) to prevent drift.

---

## ⚙️ Configuration

Modify `config.py` or `config.yaml` to change downloader behavior.

- `SAVE_DIR` – Root folder for saved videos.
- `THREAD_COUNT` – Number of download threads (default 16).
- `MAX_RETRIES` – Retry attempts when download fails.
- `COOKIE_PATH` – Path to cookie file (default `cookies.txt` in project root).

---

## 🤝 Contributing

Any form of contribution – bug reports, feature suggestions, or pull requests – is very welcome.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

Distributed under the [MIT License](LICENSE).
