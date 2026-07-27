# openjpeg 2.5.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 `ohc-run.py init-build openjpeg 2.5.4` 下载源码并初始化构建环境
2. 使用 `ohc-run.py conan-init openjpeg 2.5.4` 生成 Conan 配方
3. 使用 `ohc-run.py conan-verify openjpeg 2.5.4` 验证配方
4. `conan create` 成功编译并打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 在 OHOS 上不生成 SONAME | CMake 不识别 OHOS 平台，未设置 SONAME flag | 在 `generate()` 中设置 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,` |

## 依赖版本

无外部依赖（openjpeg 2.5.4 仅依赖 C 标准库）

## 验证结果

```
conan create 成功
test_package 通过（opj_version() + opj_create_decompress/opj_create_compress API 验证）
```

## 注意事项

- 库实际名称为 `openjp2`，而非 `openjpeg`
- 需要设置 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 修复 OHOS 上的 SONAME 问题
---

**编译结束**: 2026-07-15 21:09
**最终状态**: built
