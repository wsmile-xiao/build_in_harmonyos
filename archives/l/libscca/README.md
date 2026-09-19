# libscca

访问 Windows 预取文件（Prefetch/PF，SCCA）格式的 C 库。

## 简介

libscca 解析 Windows Prefetch（.pf）文件，提供可执行文件名、预取哈希、运行次数、最后运行时间、卷信息与文件名列表读取能力。随包构建一个终端工具：

- **sccainfo**：显示 Prefetch 文件的格式版本、可执行名、哈希、运行计数与卷/文件列表等信息

## 官网

https://github.com/libyal/libscca

## 许可证

LGPL-3.0-or-later

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 20250915 | building | 2026-09-18 | autotools | 0 |

### 平台适配要点

| 问题编号 | 说明 | 解决方案 |
|----------|------|----------|
| E007 | GNU config.guess 不识别 HarmonyOS | conanfile.py 内联补丁 config.guess/config.sub |
| E011 | HMDFS 下 umask 077 导致临时目录不可写 | configure/config.status 内 umask 077 改 022 |

## 依赖

无外部依赖。内部捆绑 libyal 系列子库（libcerror、libcdata、libbfio、libfvalue、libfwnt 等）随包编译。
