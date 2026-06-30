# squashfs

## 软件描述

squashfs 是一个压缩的只读文件系统，用于 Linux。

- **官方主页**: https://github.com/plougher/squashfs-tools
- **许可证**: GPL-2.0-or-later

## 编译状态

| 版本 | 状态 | 编译日期 | 构建系统 | 说明 |
|------|------|----------|----------|------|
| 4.7.5 | built | 2026-05-29 | makefile | gzip-only, with musl pthread_cancel stub |

## 可执行文件

- `mksquashfs` - 创建 squashfs 文件系统
- `unsquashfs` - 解压 squashfs 文件系统
- `sqfscat` - 显示 squashfs 文件内容
- `sqfstar` - 从 tar 创建 squashfs

## 编译说明

### 已知问题

1. **压缩支持受限**: 当前仅支持 gzip 压缩，缺少 LZ4/LZO/XZ/ZSTD 支持（预编译包缺少开发文件）
2. **pthread_cancel stub**: 鸿蒙 musl libc 不实现 pthread_cancel()，使用 stub 替代

### 补丁文件

- `0001-Makefile.patch` - 禁用额外压缩支持
- `0002-mksquashfs.c.patch` - pthread_cancel stub
- `0003-restore.c.patch` - pthread_cancel stub
