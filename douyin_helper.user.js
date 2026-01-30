// ==UserScript==
// @name         Douyin Downloader Helper
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Catch Douyin video streams and send to local downloader
// @author       wanjia9527
// @match        https://www.douyin.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// ==/UserScript==

(function () {
    'use strict';

    const CONFIG = {
        server: "http://127.0.0.1:5000/push_videos",
        scrollMin: 500,
        scrollMax: 3000
    };

    let autoScroll = false;
    let timer = null;
    let count = 0;

    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
        const response = await originalFetch(...args);
        const url = args[0].toString();

        if (url.includes('/aweme/v1/web/tab/feed/') || url.includes('/aweme/v1/web/aweme/post/')) {
            const clone = response.clone();
            clone.json().then(data => handleData(data)).catch(() => { });
        }
        return response;
    };

    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, url) {
        this.addEventListener('load', function () {
            const urlStr = url.toString();
            if (urlStr.includes('/aweme/v1/web/tab/feed/') || urlStr.includes('/aweme/v1/web/aweme/post/')) {
                try {
                    handleData(JSON.parse(this.responseText));
                } catch (e) { }
            }
        });
        originalOpen.apply(this, arguments);
    };

    function handleData(data) {
        const list = data.aweme_list || [];
        if (!list.length) return;

        const videos = list.map(item => {
            const video = item.video || {};
            let bestUrl = null;

            const bitRateList = video.bit_rate || [];
            const hevcCodecs = new Set(['bytevc1', 'hevc', 'h265', 'bytevc2', 'vvc', 'h266']);

            if (bitRateList.length) {
                // 按码率从高到低排序
                const sorted = [...bitRateList].sort((a, b) => (b.bit_rate || 0) - (a.bit_rate || 0));

                // 优先选择 H.264 编码的最高码率
                for (const rate of sorted) {
                    const codec = String(rate.codec_type || '').toLowerCase();
                    const gear = rate.gear_name || '';
                    const isHevc = hevcCodecs.has(codec) || gear.includes('265') || gear.toLowerCase().includes('hevc');

                    if (!isHevc) {
                        const urls = rate.play_addr?.url_list || [];
                        if (urls.length) {
                            bestUrl = urls[urls.length - 1];
                            break;
                        }
                    }
                }

                // H.264 没找到，尝试 play_addr_h264
                if (!bestUrl) {
                    const h264Urls = video.play_addr_h264?.url_list || [];
                    if (h264Urls.length) bestUrl = h264Urls[h264Urls.length - 1];
                }
            }

            // 最终回退到默认 play_addr
            if (!bestUrl) {
                const urls = video.play_addr?.url_list || [];
                if (urls.length) bestUrl = urls[urls.length - 1];
            }

            return {
                id: item.aweme_id,
                title: item.desc || "untitled",
                url: bestUrl
            };
        }).filter(v => v.url);

        if (videos.length) {
            GM_xmlhttpRequest({
                method: "POST",
                url: CONFIG.server,
                headers: { "Content-Type": "application/json" },
                data: JSON.stringify({ videos }),
                onload: (res) => {
                    const data = JSON.parse(res.responseText);
                    if (data.status === 'success') {
                        count += data.added;
                        updateUI(`Sent: ${count}`);
                    }
                }
            });
        }
    }

    function doScroll() {
        if (!autoScroll) return;

        document.dispatchEvent(new KeyboardEvent('keydown', {
            bubbles: true, keyCode: 40, key: 'ArrowDown'
        }));

        const delay = Math.random() * (CONFIG.scrollMax - CONFIG.scrollMin) + CONFIG.scrollMin;
        timer = setTimeout(doScroll, delay);
    }

    function createUI() {
        const div = document.createElement('div');
        div.style.cssText = 'position:fixed;top:80px;right:20px;width:140px;background:#000;color:#fff;padding:12px;border-radius:8px;z-index:99999;font-size:12px;text-align:center;opacity:0.9;';

        const status = document.createElement('div');
        status.id = 'dy-status';
        status.innerText = 'Ready';
        status.style.margin = '8px 0';

        const btn = document.createElement('button');
        btn.innerText = 'Start Auto-Scroll';
        btn.style.cssText = 'width:100%;padding:6px;background:#333;color:#fff;border:1px solid #555;cursor:pointer;';
        btn.onclick = () => {
            autoScroll = !autoScroll;
            btn.innerText = autoScroll ? 'Stop' : 'Start Auto-Scroll';
            btn.style.background = autoScroll ? '#ff2c55' : '#333';
            if (autoScroll) doScroll();
            else clearTimeout(timer);
        };

        div.appendChild(document.createTextNode('Douyin Helper'));
        div.appendChild(status);
        div.appendChild(btn);
        document.body.appendChild(div);
    }

    function updateUI(text) {
        const el = document.getElementById('dy-status');
        if (el) el.innerText = text;
    }

    setTimeout(createUI, 2000);
})();
