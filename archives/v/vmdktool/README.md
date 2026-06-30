# vmdktool

vmdktool — Converts raw filesystems to VMDK files and vice versa.

## 简介

vmdktool 是一个终端工具，用于在原始磁盘镜像和 VMware VMDK 格式之间进行转换。
支持流式和随机访问两种 VMDK 读写模式，支持自定义磁盘容量和压缩级别。

## 版本

- 1.4 (当前编译版本)

## 许可证

BSD-2-Clause

## 构建系统

BSD-style Makefile（无 configure 脚本）

## 依赖

- zlib（静态链接）

## 编译产物

- bin/vmdktool — 静态链接的 AArch64 ELF 可执行文件

## 源码

https://people.freebsd.org/~brian/vmdktool/
