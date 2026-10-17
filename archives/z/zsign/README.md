# zsign

跨平台 iOS 应用重签名命令行工具（fast cross-platform iOS code signing tool）。

## 简介

zsign 用于在不依赖 Xcode / macOS 的环境下对 iOS 应用包做重签名：支持 IPA、
zip、.app 文件夹、Mach-O 二进制与 zip 内文件级重签；可替换 embedded
provisioning profile、处理 entitlements、注入 dylib、编辑 bundle 元数据
（bundle id / 显示名 / 版本），并对已签包做临时目录与密钥敏感的增改。
内部使用 OpenSSL（libcrypto：CMS / PKCS12 / OCSP / X.509）与内嵌的
zlib + minizip，C++ 实现，单二进制交付。

## 官网

https://github.com/zhlynn/zsign

## 许可证

MIT

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 1.1.1 | built | 2026-09-21 | makefile | 0（零源码修改） |

### 鸿蒙适配要点

- 纯 Makefile 工程：`make -C build/linux CC=clang CXX=clang++ VERSION=<ver>
  OPENSSL_INCLUDE=-I… OPENSSL_LIB="-L… -lcrypto" -j1`，产物 `<src>/bin/zsign`。
- 必须显式传 `VERSION`（tarball 无 .git，否则版本号回退 0.0.0-dev）。
- 依赖仓内 `openssl/3.5.6`（仅 libcrypto，静态链接；`OSSL_PROVIDER_load`
  要求 OpenSSL 3.x）。
- 鸿蒙平台签名 IPA 时必须加 `-t <可写临时目录>`（zsign 默认解压到 /tmp，
  HMDFS 上 /tmp 只读）。
