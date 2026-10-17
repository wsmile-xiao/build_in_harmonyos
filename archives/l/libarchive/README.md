# libarchive

## 简介
libarchive 是多格式归档和压缩库，支持 tar、zip、cpio、ISO 等多种格式。

## OHOS 适配
- 3.7.4 版本：autotools 构建（tar.gz 格式源码）
- 3.7.7 版本：CMake 构建（tar.gz 格式源码，zlib/bzip2/xz/zstd 四压缩后端启用）
- 3.8.7 版本：autotools 构建（tar.xz 格式源码）

## 依赖
- zlib（1.3.1.1，-fPIC 静态版）
- bzip2（可选）
- xz / liblzma（可选）
- zstd（可选）
- openssl（可选）

## 功能验证
```bash
# 检查库
ls -la $HOME/usr/local/lib/libarchive*
# 检查工具
bsdtar --version
```

## 参考
- 主页: https://www.libarchive.org/
