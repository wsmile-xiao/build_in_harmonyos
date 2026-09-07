# polyglot - PolyGlot UCI↔XBoard 协议适配器与开局库工具

## 简介

PolyGlot 是 Fabien Letouzey 编写的国际象棋引擎协议适配器，把 UCI 引擎适配为
XBoard 协议（供 XBoard/WinBoard 图形界面使用）。它同时自带开局库（opening book）
工具子命令，可从 PGN 对局文件生成 Polyglot 格式二进制开局库。

## 功能特点

- 引擎适配：UCI 引擎 ↔ XBoard 协议互转（需 polyglot.ini 配置）
- `make-book`：从 PGN 生成 Polyglot 开局库（支持 -min-game 过滤）
- `merge-book`：合并两个开局库
- `dump-book`：导出开局库走子线路（white/black 视角）
- 支持各类 UCI 引擎选项透传、日志、FEN/EPD 处理等

## 官方信息

- **源码（Debian pool 权威镜像）**: https://ftp.debian.org/debian/pool/main/p/polyglot/polyglot_2.0.4.orig.tar.gz
- **上游作者**: Fabien Letouzey
- **许可证**: GPL-2.0

## 编译版本

当前已编译版本：2.0.4（官方最后正式版）

### 已知平台适配问题

1. **HMDFS umask 权限问题**（E129）
   - 上游 configure 内嵌 `umask 077`，在 HMDFS（新目录强制 setgid）上创建
     `drwx--S---` 临时目录导致 config.status 失败
   - 配方 build() 中 `sed -i 's/umask 077/umask 022/g' configure` 修复

2. **2008 年代 config.guess**
   - tarball 自带 config.guess/sub 为 2008 版本，在 OHOS 上原生探测可正常工作
     （configure 顺利通过），无需更新

## 使用示例

```bash
# 从 PGN 生成开局库
polyglot make-book -pgn games.pgn -bin book.bin -min-game 3

# 合并两个开局库
polyglot merge-book -in1 small.bin -in2 big.bin -out merged.bin

# 导出开局库走子线路
polyglot dump-book -bin book.bin -color white -out lines.txt

# 作为引擎适配器运行（需 polyglot.ini）
polyglot
```

## 编译状态

- **版本**: 2.0.4
- **状态**: built
- **编译日期**: 2026-09-03
- **构建系统**: autotools
- **依赖**: 无 conan 依赖（纯 C 标准库 + 系统 libm）
- **产物**: 单一可执行文件 `bin/polyglot`（package_type=application）
