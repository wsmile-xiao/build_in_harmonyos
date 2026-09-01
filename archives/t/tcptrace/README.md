# tcptrace — TCP 连接分析工具

## 描述

tcptrace 是一个 TCP 连接分析工具，用于分析 tcpdump 和其他网络抓包工具的输出。它可以分析 TCP 连接、计算吞吐量、重传、往返时间等。

## 版本 6.6.7
- **状态**: 已构建验证
- **构建日期**: 2026-07-24
- **构建系统**: autotools (Autoconf 2.52)
- **许可证**: GPL-2.0-or-later

## 依赖
- libpcap（网络抓包库）

## OpenHarmony 适配说明
- `config.guess`/`config.sub` 已更新以识别 `aarch64-unknown-linux-ohos`
- `pcap_offline_read` 已替换为 `pcap_dispatch`（现代 libpcap 公共 API）
- `TMPDIR` 需设置为可写目录（`/tmp` 为只读文件系统）
- `configure` 中 `umask 077` 改为 `umask 007`（HarmonyOS SGID 权限冲突）
- `Makefile.in` 安装目标适配 DESTDIR 和 `@prefix@`

## 补丁列表（5个）
1. 0001-Makefile.in.patch — DESTDIR + @prefix@ + 移除 -o/-g
2. 0002-config.guess.patch — 平台识别
3. 0003-config.sub.patch — 平台识别
4. 0004-configure.patch — umask 007
5. 0005-tcpdump.c.patch — pcap_dispatch 替换
