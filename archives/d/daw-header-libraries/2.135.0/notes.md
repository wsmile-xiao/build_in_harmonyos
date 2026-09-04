# daw-header-libraries 2.135.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only CMake INTERFACE library）
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，/data/service/hnp/bin）
- 状态: published

## 编译步骤

```bash
# 源码: beached/header_libraries v2.135.0（官方 tag）
# SHA-256: 212398602bb6c3f2fe3eb86b8ca0d1959934f51f4960e0c657490b6828beb319

# 配方验证（OHOS aarch64 profile）
conan create . --user=ohos --channel=testing \
  -pr:h ohos-aarch64 -pr:b default
# → 构建 + test_package 消费者测试 PASS（span/expected_t/string_view 核心 API）

# 上游测试全量构建与运行（C++17 默认集）
cmake -DDAW_ENABLE_TESTING=ON -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang ..
cmake --build . -j8
ctest --test-dir build-test/tests --output-on-failure -j8
# → 107/107 PASS (100%)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 从 GitHub 下载超时 | 网络不稳定 | 手动从官方 tarball 下载并放置到 $TMPDIR/builds 复用 |
| 2 | test_package 引用 daw_static_string.h 头文件不存在 | 版本 2.135.0 无 static_string 头 | 改用实际存在的 daw_string_view.h |
| 3 | daw::expected<T,E> 模板参数不匹配 | 2.135.0 为 expected_t<T> 单模板参数 | 测试改用 expected_t<T> |
| 4 | daw::array / daw::algo 命名不存在 | API 命名与文档不一致 | 改用 daw::to_array / daw::algorithm::max_element |
| 5 | C++20/23 上游测试构建崩溃 | OHOS clang 15 前端对 daw_traits_test.cpp 段错误（-Weverything -pedantic-errors） | 工具链前端问题；默认 C++17 配置不受影响，107/107 通过 |

## 源码修改

无需补丁（header-only 库，无平台适配代码修改）。

## 依赖版本

无外部依赖（仅测试链接系统 Threads）。

## 验证结果

```bash
# conan create + test_package
# → PASS: daw-header-libraries header-only 库链接和核心 API 验证通过

# 上游 ctest（C++17 默认集）
# → 100% tests passed, 0 tests failed out of 107

# HarmonyOS 专项测试（reports/daw_ohos_specific_test.cpp）
# → PASS: daw-header-libraries 2.135.0 HarmonyOS 专项测试全部通过 (clang 15.0, aarch64-ohos)
#   运行日志 SHA-256: 28f32d35b7c46917ed21cc2f52feceda392361809d4c84120e5f6f10489c686e
```

## 注意事项

- header-only 库（357 个头文件），package_type = header-library，cpp_info.libs 为空。
- CMake 目标: daw::daw-header-libraries（install EXPORT NAMESPACE daw::）。
- OHOS 适配: generate() 中 os in ("Linux","OHOS") 时注入 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（R32）。
---

**编译结束**: 2026-09-02 23:06
**最终状态**: published
