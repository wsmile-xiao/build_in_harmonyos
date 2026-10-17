# libxar

## 简介
Xar（eXtensible ARchive）——Apple 开发的可扩展档案格式，提供 libxar 库与 xar
命令行工具（创建/列出/解压 xar 档案，支持 gzip/bzip2 编码与
sha1/sha256/sha512 校验和）。macOS 系统安装包（.pkg）即采用 xar 格式。
源码取自 Apple 官方开源发行 apple-oss-distributions/xar（tag xar-498，
即 Debian/Ubuntu 的 1.8.0.498）。

## OHOS 适配
- autotools 构建（configure 预生成于 2005 年，autoconf 2.59 时代）
- 8 个补丁：config.guess/sub OHOS 识别（E007）、API_AVAILABLE 空宏、linuxattr
  函数名、OpenSSL 3 不透明 EVP_MD_CTX、MNT_LOCAL 探测、vendored musl-fts、
  CLI include 路径、getopt char→int
- umask 077→022 + mktemp 包装解决 HMDFS 临时目录权限（E011，同 xz）
- xml2-config 包装脚本解决 conan libxml2 前缀硬编码问题
- CPPFLAGS/LIBS 注入链接 OpenSSL libcrypto 摘要（configure 无对应检测）；按上游 498 默认不启用 lzma

## 依赖
- zlib / bzip2 / libxml2 / openssl(libcrypto)（lzma 按上游默认未启用）

## 功能验证
```bash
xar -c -f sample.xar <文件或目录>
xar -t -f sample.xar
xar -x -f sample.xar -C <目录>
```

## 版本
- 1.8.0.498: built (2026-09-19), 净新适配

## 参考
- 上游: https://github.com/apple-oss-distributions/xar
