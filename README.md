# 🎵 抖音批量下载器 (Douyin Downloader)

[English Version](README_EN.md) | [中文说明](README.md)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/wanjia9527/douyin_downloader?style=for-the-badge)](https://github.com/wanjia9527/douyin_downloader/stargazers)

> **一款高效、双模式的抖音视频高清下载工具。**  
> 无论你是想边刷边下（手动模式），还是想批量归档某个博主的所有作品（自动模式），本项目都能满足你的需求。

---

## ✨ 核心亮点

- **🚀 极速下载**：基于 `requests` 连接池和多线程技术（支持 16-32 线程并发），下载速度飞快。
- **🛡️ 智能过检测**：支持加载本地 Cookie (`cookies.txt`，兼容 Netscape 格式)，轻松绕过登录限制。
- **📂 自动归档**：
  - 推荐流视频 -> 存入 `保存目录/Douyin_Feed/`
  - 个人主页视频 -> 存入 `保存目录/作者昵称/`
- **🎮 双重模式**：
  - **浏览器辅助模式**：配合油猴脚本，浏览时一键自动捕获。
  - **全自动爬虫模式**：全自动后台运行，自动翻页抓取。

---

## 📈 Star 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=wanjia9527/douyin_downloader&type=Date)](https://star-history.com/#wanjia9527/douyin_downloader&Date)

---

## 🛠️ 快速开始

### 1. 安装项目

克隆仓库并安装依赖：
```bash
git clone https://github.com/wanjia9527/douyin_downloader.git
cd douyin_downloader
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置保存路径

打开 `main.py` 文件，找到并修改以下变量（设为你喜欢的盘符）：
```python
SAVE_DIR = r"F:\Douyin_Videos"  # <--- 修改这里
```

### 3. 启动核心服务
**注意：无论使用哪种模式，都必须先运行此服务！**
```bash
python main.py
```

---

## 📖 使用指南

### 模式 A：浏览器辅助（手动/半自动）
*适用场景：日常刷抖音，看到喜欢的视频或只想下载部分视频。*

1. 在浏览器安装 [Tampermonkey (油猴)](https://www.tampermonkey.net/) 插件。
2. 创建新脚本，将 [`douyin_helper.user.js`](douyin_helper.user.js) 的内容复制进去并保存。
3. 打开 [Douyin.com](https://www.douyin.com/)，你会看到右侧出现悬浮面板。
4. **开始刷视频**：脚本会自动捕获你看到的视频并发送给后台下载！

### 模式 B：全自动爬虫（批量归档）
*适用场景：无需打开浏览器，批量下载某个博主的全部作品，或者挂机下载推荐流。*

1. **设置 Cookie** (只需一次)：
   - 在浏览器安装 **EditThisCookie** 插件。
   - 登录抖音网页版 -> 点击插件图标 -> **导出** (箭头图标)。
   - 在项目根目录下新建 `cookies.txt`，将内容粘贴进去并保存。
2. **运行爬虫**：
   ```bash
   # 下载推荐流（无尽模式）
   python spider.py

   # 下载指定博主的全部作品
   python spider.py "https://www.douyin.com/user/MS4wLjABAAAA..."
   ```

---

## 🤝 参与贡献

欢迎任何形式的贡献！无论是提交 Bug 反馈、功能建议，还是直接提交 PR，都非常感谢。

1. Fork 本项目
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📝 开源协议

本项目基于 [MIT License](LICENSE) 开源。
