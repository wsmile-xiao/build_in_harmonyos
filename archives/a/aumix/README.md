# aumix

aumix 是一个基于 ncurses 的音频混音器工具，用于控制 OSS（Open Sound System）兼容的音频设备。

## 简介

aumix 提供了一个基于 ncurses 的终端界面，允许用户调整各种音频通道的音量、平衡和录音源。它支持主音量、低音、高音、合成器、PCM、麦克风、CD 等多种音频通道的控制。

该工具还包含一个 GTK+ 界面（xaumix）和一个静音脚本（mute），但在 OpenHarmony 平台上仅编译了 ncurses 界面，因为 GTK+ 2.0 不可用。

aumix 支持交互式和非交互式两种操作模式。在交互模式下，用户可以通过键盘快捷键实时调整混音器设置；在非交互模式下，可以通过命令行参数批量设置或查询混音器状态。

## OHOS 适配要点

1. **config.guess/config.sub 更新**：原始 tarball 中的 config.guess（2008年版）无法识别 ohos 平台，替换为较新版本（E007）。
2. **禁用 GTK+**：使用 `--without-gtk` 参数跳过 GTK+ 2.0 依赖，仅编译 ncurses 界面。
3. **-fcommon 编译选项**：aumix 的头文件（curses.h、common.h、interactive.h）中直接定义了全局变量而非使用 extern 声明，导致 clang/LLD 报告重复符号错误。使用 `-fcommon` 标志使 clang 将其作为 common 符号处理（兼容旧版 GCC 行为）。
4. **config.status umask 修复**：HMDFS 文件系统在 `umask 077` 下创建的目录会带有 SGID 位，导致无法在目录内创建文件。将 config.status 中的 `umask 077` 修改为 `umask 022`。
5. **autoreconf -fi**：使用 autoreconf 重新生成 configure 脚本，以利用较新的 autoconf 2.72。

## 依赖列表

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 预编译 | 终端界面库，已预装在 ~/usr/local |
| musl libc | 系统自带 | C 标准库 |

## 功能验证

```bash
# 查看帮助信息
aumix -h

# 查看版本
aumix -v

# 查询混音器设置
aumix -q
```

## 参考链接

- [aumix 官方页面](http://www.jpj.net/~trevor/aumix.html)
- [aumix SourceForge](https://sourceforge.net/projects/aumix/)
- [Debian Package](http://http.debian.net/debian/pool/main/a/aumix/)
