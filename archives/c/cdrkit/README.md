# cdrkit

cdrkit 是 CD/DVD 刻录和镜像制作工具集，是 cdrtools 的开源替代。

## 描述

cdrkit（原 mkisofs/cdrecord 的开源分支）提供 genisoimage（创建 ISO 镜像）、wodim（CD/DVD 刻录）、icedax（CD 音频提取）等工具。它是 Linux 系统下光盘操作的标准工具集。

## 已编译版本

- 1.1.11 (2026-05-30)

## 特性

- ISO 镜像创建（genisoimage）
- CD/DVD 刻录（wodim）
- CD 音频提取（icedax）
- ISO 镜像信息查询（isoinfo）

## 使用方法

```bash
# 创建 ISO 镜像
genisoimage -o output.iso /source/directory
# 刻录 ISO 到光盘
wodim -v dev=/dev/sr0 output.iso
```