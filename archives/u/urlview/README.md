# urlview

命令行 URL 抽取器 / 启动器：从文本（文件参数或标准输入）里按正则找出 URL，用 ncurses
菜单列出来，选中后交给处理命令（默认 `url_handler.sh`）打开。

- 上游：`urlview-ng`（https://sr.ht/~nabijaczleweli/urlview-ng）。它是经典 urlview 0.9
  的现役续作：把 23 年前的 autoconf 换成一份 20 行裸 Makefile，并收掉了 Debian 侧的 bug 存量。
  Debian 的**源包名**沿用 `urlview`（池路径 `main/u/urlview/`），所以版本串 `1e` 与本项目
  的 SNV 版本号（`1a`…`1e`）对应，不是"经典 urlview 的某个怪版本"。
- 版本 `1e` 的官方产物：`https://git.sr.ht/~nabijaczleweli/urlview-ng/archive/1e.tar.gz`
  （sha256 `8522c5a560def04a022faad66a1b4be5c895ecab9a93dc63c49969febcc8d571`，
  与 Debian 池件 `urlview_1e.orig.tar.gz` 逐字节同一文件；池内 `.orig.tar.gz.asc` 是上游作者
  自己的 PGP 签名，说明 .orig 不是 Debian 重打包）。
- 许可：源码主体 GPL-2.0-or-later，构建面（Makefile、quote.*、.builds）0BSD。

## 构建产物

| 路径 | 说明 |
|---|---|
| `bin/urlview` | 主程序（静态链 ncursesw） |
| `bin/url_handler.sh` | 默认 URL 处理脚本（`DEFAULT_COMMAND`），`#!/bin/sh` |
| `share/man/man1/urlview.1` | 手册页 |
| `etc/urlview.conf` | 系统级样例配置（`SYSTEM_INITFILE`） |

无头环境里 `urlview` 有一个直接可用的形态：stdout 不是 tty 时它不进菜单，只把抽到的 URL
逐行打到 stdout 后 `return 0`，因此可以被脚本消费（本包的 test_package 就建立在这条分支上）。
