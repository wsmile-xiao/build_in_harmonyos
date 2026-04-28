# libarchive

## 简介
libarchive 是多格式归档和压缩库，支持 tar、zip、cpio、ISO 等多种格式。

## OHOS 适配
- autotools 构建
- 3.7.4 版本编译成功（tar.gz 格式源码）
- 3.8.7 版本源码格式为 tar.xz

## 依赖
- zlib（可选）
- bzip2（可选）
- xz（可选）
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
