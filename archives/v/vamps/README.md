# vamps

`vamps` 将符合 DVD 标准的 MPEG-2 程序流（PS）按指定压缩因子"蒸发"瘦身：选择性复制音轨与字幕轨，并对内嵌的 MPEG-2 视频基本流重新量化（requantize），用于把 DVD-9 影片压缩到可刻录的 DVD-5 尺寸。压缩因子可只作用于视频基本流（`-e`）或整个程序流（`-E`）。

上游 [SourceForge vamps](https://sourceforge.net/projects/vamps/)（作者 Steve Nightingale，GPL-2.0-or-later）。

## 功能概述

- `vamps` — 重量化主程序（多线程）：从 stdin 读 DVD 兼容 PS，按 `-a`/`-s` 选定音轨/字幕轨复制、按 `-e`/`-E` 因子重量化视频流后写到 stdout；支持 `-i` 注入文件、`-p` 保留原始轨映射、`-S` 手工指定输入字节数
- `play_cell` — DVD 播放辅助工具：直接播放 DVD 设备/备份镜像中指定 VTS/PGC/Cell（基于 libdvdread）

## 依赖关系

- 编译依赖：`libdvdread/7.1.0`（仅 `play_cell`：头文件 `dvdread/ifo_read.h`、`dvdread/nav_read.h` + `-ldvdread`；默认静态链接，产物自包含）
- 运行依赖：无第三方库（libdvdread 静态链入；`vamps` 仅用系统 `-lm -lpthread`）
- 运行环境：`play_cell` 需要真实 DVD 设备或备份目录才有完整功能；`vamps` 为 stdin/stdout 流式工具，无设备依赖

## OHOS 适配要点

- 上游手写递归 Makefile 硬编码 `CC = gcc`，配方经 make 命令行注入 `CC`（OHOS SDK clang，R33）/`CFLAGS`/`LDFLAGS` 全量接管，构建系统无需补丁；唯一源码补丁为 `patches/0001-musl-uint-typedef.patch`（requant.c 的 musl `uint` typedef）
- `libdvdread` 取默认静态变体链入 `play_cell`，规避 SONAME 软链运行期问题（E316/E492/E505）
- 上游 `install` 目标依赖 `install(1)` 且 PREFIX 写死；本配方 `package()` 直接 copy 两个二进制（`bin/vamps`、`bin/play_cell`）与 `COPYING`
- 上游无任何测试套件（无 test 目录、无 check 目标、无测试框架绑定）；test_package 新增 5 个鸿蒙消费者冒烟用例（usage 语义 ×4 + 空 PS 输入全管线 EOF 干净关闭 ×1）
- 源码可移植性良好：`vamps.c` 自带 `_GNU_SOURCE`（musl 下 `getopt_long_only` 可用），无 linux/asm 专有头、无 lseek64/mmap

## 参考资料

- 项目主页与下载：<https://sourceforge.net/projects/vamps/>
- Debian 源码包：<https://packages.debian.org/unstable/graphics/vamps>
