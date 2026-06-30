# PHP 8.3.11 编译笔记

## 编译信息

- **软件**: php
- **版本**: 8.3.11
- **状态**: built（编译成功）
- **构建系统**: autotools
- **编译日期**: 2026-05-26

## 配置选项

```bash
./configure --prefix=/storage/Users/currentUser/usr/local --disable-all --enable-cli
```

## 平台适配问题

### 1. 源码包不完整（严重）

PHP发布的tar包缺少build目录的17+个关键文件，需要从GitHub手动下载。

### 2. pthread_cancel不支持（PSCAN-MUSL-001）

musl/OHOS不支持pthread_cancel，使用`#ifdef __OHOS__`跳过。

### 3. libtool SED路径问题

修改libtool中的SED路径为系统路径/usr/bin/sed。

## 编译产物

- php CLI: 18MB
- phpdbg: 19MB
- php-cgi: 18MB
