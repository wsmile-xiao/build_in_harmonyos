# squashfs 4.7.5 编译笔记

## 编译环境

- **平台**: OpenHarmony (aarch64)
- **编译日期**: 2026-05-29
- **构建系统**: Makefile

## 编译步骤

### 1. 源码下载

使用官方 GitHub 源下载：
```
URL: https://github.com/plougher/squashfs-tools/archive/refs/tags/4.7.5.tar.gz
```

### 2. 编译配置

由于预编译包缺少开发文件（lz4, lzo, xz, zstd），禁用额外压缩支持：
```
make XZ_SUPPORT=0 LZO_SUPPORT=0 LZ4_SUPPORT=0 ZSTD_SUPPORT=0
```

### 3. 遇到的问题

#### 问题 1: pthread_cancel 未实现

**描述**: 链接时报错 `undefined reference to 'pthread_cancel'`

**原因**: 鸿蒙系统使用 musl libc，不实现 pthread_cancel() 函数

**解决方案**: 创建 stub 头文件，提供空实现

#### 问题 2: 压缩支持受限

**描述**: 无法启用 LZ4/LZO/XZ/ZSTD 压缩

**原因**: cmd-pkgs 预编译包缺少开发文件（头文件和 pkg-config 文件）

**解决方案**: 禁用额外压缩支持，仅保留 gzip

### 4. 验证

```
$ mksquashfs --version
mksquashfs version 4.7.5 (2026/05/29)

$ unsquashfs --version
unsquashfs version 4.7.5 (2026/05/29)
```

## 功能限制

当前版本仅支持 gzip 压缩。如需完整功能，需要手动编译 lz4、lzo、xz、zstd 库。

## 补丁说明

| 补丁 | 描述 |
|------|------|
| 0001-mksquashfs-pthread-cancel-stub.patch | mksquashfs.c 中 pthread_cancel stub |
| 0002-restore-pthread-cancel-stub.patch | restore.c 中 pthread_cancel stub |
| 0003-pthread-cancel-stub-header.patch | pthread_cancel stub 头文件 |
---

**编译结束**: 2026-07-16 01:04
**最终状态**: built
