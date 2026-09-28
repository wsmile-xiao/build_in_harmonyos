# mpdas

MPD（Music Player Daemon）的轻量「正在播放」客户端：连上本机/远端 MPD，取出当前曲目的
艺术家与曲名，按可配置格式打印到标准输出（供 xmobar / polybar / dzen2 等状态栏消费），
并把它 scrobble 到 Last.fm 或 Libre.fm。

- 上游主页：<https://50hz.ws/mpdas/>
- 上游代码库：<http://github.com/hrkfdn/mpdas>（作者主页页面链接）
- 许可证：ISC
- 语言：C++
- 构建系统：makefile

## 版本

| 版本 | 状态 | 归档 |
|---|---|---|
| 0.4.5 | built | `0.4.5/` |

## 依赖

| 依赖 | 用途 |
|---|---|
| libmpdclient | MPD 协议客户端 |
| libcurl | Last.fm / Libre.fm scrobble 的 HTTPS 通道 |
