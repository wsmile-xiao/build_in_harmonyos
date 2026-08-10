# lzbench 2.2 — OpenHarmony 编译记录

## 基本信息
- 软件: lzbench
- 版本: 2.2
- 构建系统: Makefile (plain make, no configure, no install)
- 目标: ohos-aarch64
- 源码: https://github.com/inikep/lzbench/archive/refs/tags/v2.2.tar.gz
- License: GPL-2.0-or-later

## 编译指导
- 使用 `make CC=clang CXX=clang++ -j1` 构建
- Makefile 自动检测 clang 编译器和 aarch64 架构
- 无 configure 步骤, 无 make install, 手动复制 lzbench 二进制
- 密度压缩器 (Density) 因缺少 cargo 自动跳过

## 补丁清单
- `patches/0001-lz-zstd-lib-common-zstd_deps.h.patch`: 排除 __OHOS__ 平台定义 _GNU_SOURCE,
- `patches/0002-lz-zstd-lib-dictBuilder-cover.c.patch`: 排除 __OHOS__ 平台定义 _GNU_SOURCE,
  避免 zstd cover.c 中 qsort_r 链接错误 (HarmonyOS libc 不提供 qsort_r)
  修改文件:
  - lz/zstd/lib/common/zstd_deps.h
  - lz/zstd/lib/dictBuilder/cover.c

## 已知限制
- Density 压缩器因缺少 Rust/cargo 自动跳过 (不影响核心功能)
- LZSSE 因需要 SSE4.1 (x86 only) 自动跳过
- CUDA 压缩器因缺少 CUDA Toolkit 自动跳过

## 功能验证
- `lzbench -V` 输出版本信息: lzbench 2.2
- `lzbench -ezstd <file>` 成功压缩和解压测试文件
