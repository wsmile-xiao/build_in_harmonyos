# alpine-make-rootfs

alpine-make-rootfs 是一个创建 Alpine Linux 根文件系统镜像的工具，用于容器和嵌入式系统。

## 描述

alpine-make-rootfs 基于 Alpine Linux 的 apk 包管理器创建最小化的根文件系统镜像。它支持自定义包选择、镜像源配置和脚本钩子，是构建轻量容器镜像的基础工具。

## 已编译版本

- 0.8.1 (2026-05-27)

## 特性

- 创建最小化 Alpine rootfs
- 自定义包选择
- 支持脚本钩子配置

## 使用方法

```bash
# 创建 Alpine rootfs
alpine-make-rootfs -p "busybox,apk-tools" output.tar.gz
```