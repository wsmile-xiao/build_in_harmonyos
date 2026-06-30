# jhead

**描述**: Extract Digicam setting info from EXIF JPEG headers — 从 JPEG 文件的 EXIF 头中提取数码相机设置信息。

**主页**: http://www.sentex.net/~mwandel/jhead

**源码**: https://github.com/Matthias-Wandel/jhead

**许可证**: Public Domain

**语言**: C

## 功能概述

jhead 是一个轻量级的命令行工具，用于读取和修改 JPEG 文件中的 EXIF 元数据信息，包括：
- 显示数码相机拍摄参数（相机型号、焦距、曝光时间等）
- 日期/时间调整（时间偏移、文件时间同步等）
- 注释插入、提取、替换、删除
- 缩略图操作（删除、替换、提取）
- 基于日期的文件重命名和目录归档
- IPTC/XMP 数据操作
- JPEG 文件净化（-purejpg）

## 鸿蒙适配要点

- 构建系统：简单 Makefile（无 autotools configure）
- 必须使用 GNU ld.bfd 替代有缺陷的 SDK lld（依赖损坏的 libxml2）
- DESTDIR 模式需要将 PREFIX 和 DESTDIR 分离（原始 Makefile 将 DESTDIR 嵌入 PREFIX）
- jhead 使用 `-V` 参数查看版本号，而非 `--version`

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 3.08 | published | 2026-06-06 |