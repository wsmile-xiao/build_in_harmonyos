# span-lite 0.11.0 — 适配笔记

## 来源核验（Bootstrap）
- 上游 URL: https://github.com/martinmoene/span-lite
- 官方 tag: v0.11.0
- 官方 release commit（GitCode 镜像核对）: `50f55c59d1b66910837313c40d11328d03447a41`
- tarball SHA-256: `ef4e028e18ff21044da4b4641ca1bc8a2e2d656e2028322876c0e1b9b6904f9d`
  （自 https://codeload.github.com/martinmoene/span-lite/tar.gz/refs/tags/v0.11.0 下载核验）
- CMakeLists.txt 声明 `project(span-lite VERSION 0.11.0)`，结构与版本一致
- 许可: BSL-1.0（LICENSE.txt）

## 库特征
- header-only 单文件头: `include/nonstd/span.hpp`
- CMake INTERFACE library，target 名 `nonstd::span-lite`
- 无任何第三方依赖
- 上游自带 Conan 1.x 配方（conanfile.py 使用 `from conans import ...`），按本项目 Conan 2.x 规范重写为 header-library 配方

## 上游测试（原生，clang 15.0.4）
- 配置: `cmake -DSPAN_LITE_OPT_BUILD_TESTS=ON -DSPAN_LITE_OPT_BUILD_EXAMPLES=OFF`
- 构建 4 个测试二进制: span-lite-cpp98.t / cpp11.t / cpp14.t / cpp17.t
- 全部运行 exit_code=0；上游测试源 `test/span.t.cpp` 含 131 个 CASE 用例

## 适配结论
- 常规 header-only 基础适配，无系统依赖、无特殊架构问题 → 路径 A 常规基础适配（【积分赛】前缀）
- 暂无通用可复用问题，不生成知识草稿（路径 B 不成立）
---

**编译结束**: 2026-09-01 18:10
**最终状态**: built
