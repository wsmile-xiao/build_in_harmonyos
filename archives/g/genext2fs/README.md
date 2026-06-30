# genext2fs

## 简介

genext2fs 是一个用于生成 ext2 文件系统镜像的命令行工具。它可以在普通用户（非 root）权限下创建 ext2 文件系统，常用于嵌入式系统开发中生成根文件系统镜像。

## 功能分类

文件操作类

## 许可证

GPL-2.0-or-later

## 已编译版本

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|----------|----------|
| 1.6.2 | published | 2026-06-12 | autotools |

## 主要特性

- 普通用户（非 root）即可生成 ext2 文件系统镜像
- 支持从目录复制文件到镜像（-d 选项）
- 支持设备表（device table）创建设备节点（-D 选项）
- 支持从 tar 归档生成文件系统（-a 选项）
- 支持符号链接
- 支持扩展属性（xattr）
- 可指定块大小、inode 数量等参数
- 支持 squash（压缩 uid/权限）

## 平台适配说明

### 鸢鸿蒙注意事项

1. 原 tarball 不含 configure 脚本，需先运行 `autoreconf -fi`
2. HMDFS 上 config.status 创建临时目录的 umask 077 需改为 022（否则 Permission denied）
3. e2fsck 在鸢鸿蒙不可用，xattr 测试无法验证（平台限制，不影响核心功能）

## 源码

- 上游地址: https://github.com/bestouff/genext2fs
- 下载 URL: https://github.com/bestouff/genext2fs/archive/refs/tags/v1.6.2.tar.gz