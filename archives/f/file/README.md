# file

## 简介
file 是一个通过检查文件内容来识别文件类型的命令行工具（即 `file` 命令），支持识别 ELF、压缩文件、文本文件等多种格式，是 Linux/Unix 系统中的基础工具之一。

## OHOS 适配
- **必须使用静态链接**: 鸿蒙 SELinux 限制导致动态链接的 `.so` 软链接无法被加载
  - 配置: `--enable-static --disable-shared LDFLAGS=-static`
- **禁用 libseccomp**: 鸿蒙不提供此库，需 `--disable-libseccomp`
- **config.sub 修补**: 需添加 `linux-ohos*` kernel-os 白名单
- **多文件修补**: man page 和源文件中有硬编码路径需修正
- **支持格式识别**: ELF、zlib、bzip2、xz/lzma ✅；zstd、lz4 ❌

## 依赖
- 编译工具: clang, make
- 压缩库（可选）: zlib, bzip2, xz/lzma

## 功能验证
```bash
file --version            # file-5.45
file /bin/sh              # ELF 64-bit LSB executable...
file archive.tar.gz       # gzip compressed data...
```

## 参考
- 官网: https://www.darwinsys.com/file/
- 源码: https://astron.com/pub/file/
