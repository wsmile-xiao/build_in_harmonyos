# Zstandard (zstd)

## 简介
Facebook 开发的快速实时压缩算法，提供高压缩比和高速解压，广泛用于数据存储和传输。
提供 `libzstd` 共享库和 `zstd`/`unzstd`/`zstdcat` 等命令行工具。

## OHOS 适配
- cmake 构建，平台兼容性好
- musl 无 GNU qsort_r：cover.c/zstd_deps.h 加 `__OHOS__` 例外
- 自发现 ohos.toolchain.cmake + 裸 cmake 构建

## 依赖
- 标准 C 库

## 功能验证
```bash
zstd --version
echo "test" | zstd | zstd -d
```

## 版本
- 1.5.6: published (2026-04-21)
- 1.5.7.1: built (2026-08-09)，cmake 配方，共享库 + 命令行工具

## 参考
- 官网: https://facebook.github.io/zstd/