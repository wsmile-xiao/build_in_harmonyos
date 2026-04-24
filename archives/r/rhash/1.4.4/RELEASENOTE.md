# RHash v1.4.4 Release Note

## 发布信息

- 版本: 1.4.4
- 状态: success
- 发布日期: 2026-04-24
- 构建系统: makefile

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang 15.0.4
- 目标架构: aarch64
- 编译模式: 静态链接

## 编译配置

```bash
./configure --prefix=$HOME/usr/local \
    --enable-static \
    --disable-lib-shared \
    --disable-gettext
make -j$(nproc)
```

## 测试结果

- 主程序测试: 24/24 通过 ✅
- 库测试: 所有哈希算法工作正常 ✅

## 支持的哈希算法

CRC32, CRC32C, MD4, MD5, SHA1, SHA256, SHA512, SHA3, AICH, ED2K, TTH, BTIH, Tiger, GOST R 34.11-94, GOST R 34.11-2012, RIPEMD-160, HAS-160, EDON-R, Whirlpool, Blake2b, Blake2s

## 鸿蒙适配说明

1. 使用静态编译模式以避免 HMDFS 文件系统软链接限制
2. 禁用 gettext 国际化支持（编译兼容性问题）
3. 由于 `install` 命令不存在，使用手动安装方式

## 交付产物

- `rhash-1.4.4-ohos-aarch64.tar.gz` (820KB)
- `rhash-1.4.4-ohos-aarch64-debug.tar.gz` (调试符号)
- `install-rhash-1.4.4.sh` (安装脚本)

## 安装方式

```bash
tar -xzf rhash-1.4.4-ohos-aarch64.tar.gz
cd pkg-rhash-1.4.4
./install-rhash-1.4.4.sh

# 验证
rhash --version  # RHash v1.4.4
```

## 已知限制

- 无国际化支持（gettext 禁用）
- 仅静态库 librhash.a，无共享库
- 无 ELF 签名（静态编译）

## 文件清单

```
bin/rhash         - 主程序
lib/librhash.a    - 静态库
```