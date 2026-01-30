# 🎵 Douyin Downloader (Hybrid Edition)

[English Version](README_EN.md) | [中文说明](README.md)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/wanjia9527/douyin_downloader?style=for-the-badge)](https://github.com/wanjia9527/douyin_downloader/stargazers)

> **A powerful, dual-mode solution for downloading high-quality videos from Douyin (TikTok China).**  
> Whether you want to browse and pick videos manually, or scrape a creator's entire profile automatically, this tool has you covered.

---

## ✨ Features

- **🚀 High Performance**: Built with `requests` connection pooling and multi-threaded downloading (16-32 threads).
- **🛡️ Smart & Safe**: Automatically handles cookies via `cookies.txt` (Netscape format) to bypass login restrictions safely.
- **📂 Auto-Organization**: 
  - Feed videos -> `Save_Dir/Douyin_Feed/`
  - Profile videos -> `Save_Dir/Author_Name/`
- **🎮 Dual Modes**: 
  - **Browser Assistant**: Use a UserScript button while browsing.
  - **Auto Spider**: Fully automated headless scraper using Playwright.

---

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=wanjia9527/douyin_downloader&type=Date)](https://star-history.com/#wanjia9527/douyin_downloader&Date)

---

## 🛠️ Quick Start

### 1. Installation

Clone the repo and install dependencies:
```bash
git clone https://github.com/wanjia9527/douyin_downloader.git
cd douyin_downloader
pip install -r requirements.txt
playwright install chromium
```

### 2. Configuration

Open `main.py` and set your preferred storage path:
```python
SAVE_DIR = r"F:\Douyin_Videos"  # <--- Change this to your path
```

### 3. Run the Core Server
**Always keep this running!** It acts as the download manager.
```bash
python main.py
```

---

## 📖 Usage Guide

### Mode A: Browser Assistant (Manual)
*Best for: Casual browsing and selective downloading.*

1. Install [Tampermonkey](https://www.tampermonkey.net/) extension.
2. Create a new script and copy the content from [`douyin_helper.user.js`](douyin_helper.user.js).
3. Open Douyin.com, scroll, and watch the server console automatically catch videos!

### Mode B: Auto Spider (Fully Automated)
*Best for: Archiving profiles or bulk downloading feeds.*

1. **Cookie Setup** (Crucial):
   - Install **EditThisCookie** extension.
   - Login to Douyin -> Export Cookies -> Paste into `cookies.txt`.
2. **Run Spider**:
   ```bash
   # Download Recommendation Feed
   python spider.py

   # Download Specific User
   python spider.py "https://www.douyin.com/user/MS4wLjABAAAA..."
   ```

> **💡 Tip**: 
> 1. Edit `SCROLL_INTERVAL = 2` in `spider.py` to adjust scrolling speed.
> 2. Default URL is now locked to Recommendation Feed (`/?recommend=1`).

---

## 🤝 Contribution

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
