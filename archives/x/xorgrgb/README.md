# xorgrgb（X.org RGB 颜色数据库工具）

## 简介

xorgrgb 是 X Window System 的颜色数据库工具，提供 `showrgb` 命令用于查询 X11 颜色名称与 RGB 值的映射关系。核心数据文件 `rgb.txt` 包含 782 条颜色定义，是 X11 应用程序颜色名称解析的基础.

**主要组件**：
- `showrgb`：命令行工具， 输出颜色数据库内容
- `rgb.txt`：颜色名称→RGB 值映射数据文件（782 条记录）

## 软件信息

- **上游源码**: https://gitlab.freedesktop.org/xorg/app/rgb
- **分类**: X11 工具
- **许可证**: MIT/X11
- **源码托管**: freedesktop GitLab（注意：非 GitHub）

## 鸿蒙适配要点

| 要点 | 说明 |
|------|------|
| 源码地址 | freedesktop GitLab，URL格式: `rgb-rgb-{ver}.tar.gz` |
| 依赖 | xorgproto（X11头文件）、util-macros（m4宏） |
| HMDFS | E011：configure 中 umask 077 需改为 umask 022 |
| 构建模式 | 默认 text 模式只生成 showrgb，不生成 rgb 二进制 |
| PKG_CHECK | xorg-macros 生成的 pkg-config 检查语法异常，不阻塞编译 |

## 可用版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.1.1 | ✅ published | 2026-06-17 |

## 预编译依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| xorgproto | 2024.1 | X11 协议头文件 + pkg-config |
| util-macros | 1.20.2 | X.Org autotools m4 宏 |

## 补丁清单

| 补丁 | 说明 | 类型 |
|------|------|------|
| 0001-configure.patch | E011: HMDFS umask 077→022 | 平台 |
