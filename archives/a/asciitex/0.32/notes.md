# asciitex 0.32 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-24
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built

## 编译步骤

1. 源码下载并解压：`https://github.com/larseggert/asciiTeX/archive/refs/tags/asciiTeX-0.32.tar.gz`
2. CMake 配置：
   ```bash
   cmake .. -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
     -DDISABLE_TESTING=ON
   ```
3. 编译：`cmake --build .`
4. 编译成功，生成 `asciitex` ELF 二进制文件（arm64, 53280 bytes）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败：cmake_minimum_required(VERSION 3.0) 与 CMake 4.1.2 不兼容 | CMake 4.x 移除了对 < 3.5 版本的兼容 | 设置 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | 链接器错误：lld 找不到 libxml2.so.16 | OHOS SDK 自带的 lld 依赖 libxml2.so.16 但该库不在系统中 | 使用 `-fuse-ld=/data/service/hnp/bin/ld` 指定 GNU ld |
| 3 | POST_BUILD 命令执行失败：Permission denied | OHOS 平台不允许执行未签名的 ELF 二进制 | 设置 `-DDISABLE_TESTING=ON` 跳过构建时测试执行 |
| 4 | 二进制无法在任何用户目录执行 | OHOS SELinux 策略限制未签名 ELF 执行 | CI 流水线 sign.sh 签名后可执行 |

## 源码修改

无源码修改。所有问题通过 CMake 配置参数解决，未修改 CMakeLists.txt 或源代码。

## 依赖版本

无外部依赖。asciitex 是纯 C 项目，自包含，无任何外部库依赖。

## 验证结果

```bash
# 编译验证（成功）
cmake --build .
# [100%] Linking C executable asciitex
# [100%] Built target asciitex

# 二进制信息
file build/asciitex
# ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 注意：二进制在当前环境下无法执行（未签名），CI 流水线签名后可执行
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| asciitex | 53280 bytes | ELF arm64 可执行文件 |

## 注意事项

- CMake 版本兼容性：CMakeLists.txt 使用 `cmake_minimum_required(VERSION 3.0)`，在 CMake 4.x 上需要设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- 链接器：OHOS 上默认 lld 有 libxml2.so.16 依赖问题，conanfile.py 中通过 `shutil.which("ld")` 动态检测 GNU ld 并通过 CMakeToolchain 传入 `-fuse-ld` 标志
- 测试执行：上游 CMake POST_BUILD 命令在构建时执行二进制，在 OHOS 上因未签名而失败，通过 `DISABLE_TESTING=ON` 禁用；test_package 使用 `asciitex -v` 验证二进制
---

**编译结束**: 2026-08-24 11:59
**最终状态**: built
