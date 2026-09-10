# colortest

`colortest` 是终端颜色测试工具集：提供 8/16/256 色显示图表与颜色测试脚本，
用于验证终端对 ANSI 颜色序列的支持情况。

Upstream: https://www.colortest.org/（官网已改版，源码取自 Debian 官方 pool 保留的 orig 包）

Pure shell/perl script tool — no compiled artifacts; runtime requires `perl`（colortest/256colors2.pl）
and `bash`（colortable16.sh）；8colors.sh/16colors.sh 由 `/bin/sh` 解释。

包含脚本：
- `colortest` — XTERM 256Color Test Chart（perl）
- `256colors2.pl` — 256 色显示（perl，来自 xterm 发行版）
- `8colors.sh` — 8 色测试图案（sh，无限循环动画，Ctrl+C 退出）
- `16colors.sh` — 16 色测试图案（sh，无限循环动画，Ctrl+C 退出）
- `colortable16.sh` — 16 色表（bash）
