# pms

> 基于 ncurses 的交互式 MPD（Music Player Daemon）客户端，Vim 风格操作

## 简介

pms（Practical Music Search）是一款运行在终端里的 MPD 客户端：浏览音乐库、搜索与排序歌曲、管理播放队列、控制播放/暂停/切歌，界面基于 ncurses 并支持高度可配置的快捷键绑定。本仓库提供 pms 0.42 在 HarmonyOS（OpenHarmony）PC aarch64 平台的 Conan 配方，构建产物为可执行程序 `bin/pms`。

## OHOS 适配要点

- 上游 0.42 为 2010 年的 autoconf 2.65 构建：CI 上显式传入 `--build/--host=aarch64-unknown-linux-ohos`（HMDFS 上 config.guess 无法探测）。
- configure 内的 `umask 077` 改为 022，并固定 Autotools 时间戳顺序，避免 make 重调 CI 不存在的 aclocal/automake。
- 该年代 configure 不提供 `--disable-nls`，完整启用 NLS，依赖制品仓 gettext/0.22.5.1（libintl + msgfmt）。
- glib 2.0 通过 pkg-config 探测，ncurses 通过自带 m4/ncurses.m4 探测；libmpdclient 由源码内嵌，无需外部 MPD 库。
- CC/CXX 取自 Conan profile（R33），并在 make 命令行透传，覆盖老 Makefile.in 里写死的 `cc`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.88.0.1 | GLIB_CFLAGS/GLIB_LIBS（pkg-config） |
| ncurses | 6.6 | 终端界面渲染（MP_WITH_CURSES 探测） |
| gettext | 0.22.5.1 | NLS（libintl + msgfmt） |

## 功能验证

```bash
pms -v
# 输出: Practical Music Search v0.42 ...（随后按上游逻辑返回退出码 4）
pms --help
# 输出: Usage: ...（含 -h 连接选项说明）
```

## 参考

- [SourceForge 项目页](https://sourceforge.net/projects/pms/)
- [官方文档站](https://ambientsound.github.io/pms)
- [源码仓库（Go 重写版，含 0.42.x 分支说明）](https://github.com/ambientsound/pms)
