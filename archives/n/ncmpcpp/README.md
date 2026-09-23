# ncmpcpp

> 功能丰富的基于 ncurses 的 MPD(Music Player Daemon)客户端

## 简介

ncmpcpp 是一款交互式命令行音乐播放客户端，提供完整的播放列表管理、媒体库浏览、标签编辑(支持批量编辑与标签工作队列)、搜索引擎、可视化器(Lyrics/Spotify 风格)以及 Last.fm 集成等功能。其界面基于 ncurses，支持鼠标、快捷键绑定与高度可配置的 UI 布局。

本仓库提供 ncmpcpp 0.10.1 在 HarmonyOS(OpenHarmony)PC aarch64 平台的 Conan 配方，构建产物为可执行程序 `bin/ncmpcpp`。

## OHOS 适配要点

- 上游 release 包未携带 `configure`，配方内置预生成的 Autotools 文件(`files/autotools-generated/`)，无需 CI 提供 aclocal/automake。
- OHOS 制品库无 GNU readline，补丁用内置兼容层替换(readline()/rl_* API)，curses 输入循环为其提供支持。
- OHOS boost/1.90.0.1 缺少编译版 regex/locale 组件，`boost::regex` 迁移为 `std::regex`、`boost::locale` 迁移为内置 UTF-8 编解码与 ASCII toLower。
- boost/1.90.0.1 未打包 header-only 的 `boost/format`，配方随附 Boost 1.84(BLS-1.0)缺失头文件并通过 `-I vendor-boost` 提供。
- 构建需显式 `--build/--host=aarch64-unknown-linux-ohos`(HMFDS 上 config.guess 无法探测)，configure 内 `umask 077` 需替换为 022，并固定 Autotools 时间戳顺序避免 make 重新调用 aclocal/automake。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.90.0.1 | filesystem/program_options/date_time/thread 等(全部 header + 编译组件) |
| libmpdclient | 2.23 | MPD 协议客户端库 |
| ncurses | 6.5 | ncursesw，界面渲染(静态) |
| curl | 8.15.0 | 网络/Last.fm/歌词抓取 |

## 功能验证

```bash
ncmpcpp --version
# 输出: ncmpcpp 0.10.1
```

## 参考

- [官方网站](https://ncmpcpp.rybczak.net)
- [源码仓库](https://github.com/ncmpcpp/ncmpcpp)
