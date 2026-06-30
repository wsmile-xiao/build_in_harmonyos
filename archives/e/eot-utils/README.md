# eot-utils

EOT（Embedded OpenType）字体工具集，用于在 OTF/TTF 字体与 EOT 格式之间转换。

## 软件描述

eot-utils 是由 W3C 开发的两个命令行工具：

- **mkeot** — 从 OpenType 或 TrueType 字体文件和一个或多个 URL 生成 EOT（嵌入式 OpenType）文件
- **eotinfo** — 以人类可读的方式显示 EOT 文件头部信息

EOT 是一种字体嵌入格式，主要用于网页字体（Web Fonts）。它允许将字体文件绑定到特定 URL，从而控制字体的使用范围。

## 源码

- 上游: https://www.w3.org/Tools/eot-utils/
- 许可证: 见 COPYING 文件

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.1 | published | 2026-06-18 |

## 依赖

无外部依赖（纯 C 实现，仅需标准 C 库）。
