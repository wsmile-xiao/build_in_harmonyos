# nload

## 简介

nload 是一个实时网络流量监控工具，通过 ncurses TUI 界面展示网络接口的进出流量统计、速率曲线图和数据总量。

- **官网**: https://github.com/rroland/nload
- **License**: GPL-2.0+

## 版本列表

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 0.7.4 | published | 2026-05-25 | 首次鸿蒙编译 |

## 功能特性

- 实时显示网络接口进出流量
- 提供流量速率曲线图
- 支持多种流量单位显示（Bit/s, kBit/s, MBit/s, Byte/s 等）
- 支持多网络接口同时监控
- 可自定义刷新间隔、时间窗口等参数
- 运行时可通过 F2 键调整设置    

## 使用方式

```bash
# 基本使用（自动检测所有网络接口）
nload

# 查看帮助
nload --help

# 指定刷新间隔 200ms
nload -t 200

# 多设备模式（不显示流量图）
nload -m

# 指定特定网络接口
nload eth0

# 使用 MByte/s 作为流量单位
nload -U M
```

## 依赖

- ncurses (>= 6.4) — TUI 界面库
- ncurses form 库 — 表单交互功能

## 鸿蒙适配说明

- 需替换 config.guess/config.sub 为支持 linux-ohos 的版本
- 需 CPPFLAGS/LDFLAGS 指向 ncurses 头文件和库路径
- HMDFS 平台上 config.status 需修改 umask 077→002