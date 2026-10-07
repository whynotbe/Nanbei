---
name: win-env-quirks
description: 用户本机(Git Bash/Win11)的环境坑:代理7897、python是坏壳要用py、py看不见/tmp
metadata:
  node_type: memory
  type: reference
  originSessionId: sess_20ffc10f-a0ba-4e3a-8950-244efb4997ce
---

用户本机环境(Windows 11 + Git Bash)已验证的事实(2026-10-03):

- **外网**:直连不通,必须走本机代理 `127.0.0.1:7897`(Clash 系)。Git Bash 里需手动 `export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897`(浏览器代理不传给命令行)。用户有时忘了开代理,遇到全部超时先探测端口:`(echo > /dev/tcp/127.0.0.1/7897)`。
- **Python**:`python` 命令是微软商店坏壳(任何参数都 rc=49 无输出),必须用 `py`(Python 3.14,真实路径 AppData\Local\Programs\Python\Python314)。
- **路径**:`py` 是 Windows 原生进程,看不见 Git Bash 的 `/tmp` 虚拟路径——跨 shell 传文件一律用真实路径(如 `/c/Users/L_why/.zcode/workspace/default/`)。
- **下载大文件**:本代理跑大文件(~30MB+)会中途断(curl error 18),用断点续传循环解决:每次向 libgen.li 的 ads.php 取新 key,`curl -C -` 接着拉,几轮即成。可用书籍源:libgen.li(annas-archive 各域名/li 弃售、/gs 是壳、/org 握手失败;archive.org 通但无中文现代书)。libgen.li 的 get.php 偶发 502,换同书另一 md5 即可。
- 下载脚本留存:`/c/Users/L_why/.zcode/workspace/default/books/fetch_book.sh`(小文件)与 `fetch_big.sh`(续传循环)+ `fetch_link.py`。

关联项目:[[cbdb-commercial-game-research]]
