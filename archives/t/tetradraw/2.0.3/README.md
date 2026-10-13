# tetradraw 2.0.3

tetradraw 是 Linux/Unix 上的 ANSI 美术编辑器 (`tetradraw`) 与查看器
(`tetraview`), 基于 ncursesw TUI。此仅适配 OHOS aarch64。

- 源码: <http://tetradraw.sourceforge.net/> (2.0.3 tarball 由
  <https://deb.debian.org/debian/pool/main/t/tetradraw/> 权威再分发)
- 版本: 2.0.3 (GPL-2.0-only)

## 已知限制

两个程序都是全屏 TUI, 运行时需要环境提供 `TERM` 对应的 terminfo 数据库;
本包不打包 terminfo 数据。
