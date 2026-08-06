# ccache 4.12.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. 源码: https://github.com/ccache/ccache/archive/refs/tags/v4.12.1.tar.gz
2. 构建系统: CMake (ccache 自带 CMakeLists.txt)
3. 依赖管理: DEPS=DOWNLOAD (FetchContent 自动下载 blake3, fmt, hiredis, xxhash, zstd 等)
4. 存储后端: file, http, redis 全部启用 (无裁剪)
5. 测试: ENABLE_TESTING=OFF (构建时), test_package 验证 ccache --version

## 依赖说明
ccache 通过 CMake FetchContent 管理所有第三方依赖，不需要预先发布 conan 包:
- Blake3 1.8.2 (BUNDLED)
- CppHttplib 0.20.0 (BUNDLED)
- Fmt 11.1.4 (BUNDLED)
- Hiredis 1.3.0 (DOWNLOADED)
- NonstdSpan 0.11.0 (BUNDLED)
- TlExpected 1.1.0 (BUNDLED)
- Xxhash 0.8.3 (DOWNLOADED)
- Zstd 1.5.7 (DOWNLOADED)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 版本显示 unknown | git clone 创建的 tarball 缺少 git archive 格式标记 | 使用 GitHub 官方 archive URL (conandata.yml) |
| 2 | CMake 警告 "System is unknown" | CMake 不识别 HarmonyOS | OHOS conan 适配版自动映射 CMAKE_SYSTEM_NAME=HarmonyOS, 警告不影响构建 |
---

**编译结束**: 2026-08-06 02:55
**最终状态**: built
