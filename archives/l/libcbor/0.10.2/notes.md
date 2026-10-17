# libcbor 0.10.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-01
- 编译器: clang/clang++ (clang 15.0.4, aarch64-linux-ohos)
- 状态: published

## 编译步骤

1. 官方源码: `https://github.com/PJK/libcbor/archive/refs/tags/v0.10.2.tar.gz`（SHA-256 `e75f712215d7b7e5c89ef322a09b701f7159f028b8b48978865725f00f79875b` 已核验）
2. CMake 配置（conan create 内自动执行，profile `ci/conan/profiles/ohos-aarch64`）：
   ```bash
   conan create archives/l/libcbor/0.10.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
   ```
   配方 generate() 注入 `BUILD_SHARED_LIBS=OFF`（静态）、`CBOR_PRETTY_PRINTER=ON`、`CMAKE_POLICY_VERSION_MINIMUM=3.5`
3. make 构建 static library `libcbor.a`
4. ctest 全量运行上游测试（26 个 `*_test` 二进制 + cpp_linkage_test）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败 "Compatibility with CMake < 3.5 has been removed" | 上游 CMakeLists.txt 声明 `cmake_minimum_required(3.0)`，本环境 CMake 4.1.2 已移除对 <3.5 的兼容 | 配方 build() `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})` |
| 2 | 上游 `float_ctrl_encoders_test` 2 用例失败 | 上游已知 issue #271：NaN payload 为编译器/平台实现定义，本平台 clang 将 `nan("3")` payload 映射为 0 | 属平台差异，如实计入台账（276/279 通过，98.6%） |
| 3 | 上游 `pretty_printer_test` SIGABRT | OHOS 环境 `tmpfile()` 返回 NULL（Permission denied），`cbor_describe(item, NULL)` 崩溃 | 环境限制；已用显式 fopen 验证 `cbor_describe` 功能正常 |
| 4 | test_package 空壳测试 | 默认模板只 printf 不调用库 API，违反 R34 | 重写 test.c：真实 uint/string/array 编解码回环 + 新增 ohos_special_test.c |

## 源码修改

无源码补丁（patches/ 为空），仅配方与测试文件。

## 依赖版本

- cmocka 2.0.2（上游测试依赖，来自 ohpcd 制品仓）
- 无运行时依赖（纯 C 库）

## 验证结果

```bash
# 上游测试（本环境实测）: 279 用例，276 通过，3 失败（2 平台差异 + 1 tmpfile 环境限制）
# 全量通过率: 276/279 = 98.9%（失败项均已记录根因，非适配缺陷）
# HarmonyOS 专项测试: 宽整型精确字节/大字节串/嵌套 map-array/流式解码 → ALL PASSED
# 消费者测试: uint/string/array 编解码回环 → ALL PASSED
# conan-verify G0-G2 + W3 本地 CI → 通过（.ci-result.json exit_code=0）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（静态库，libs=['cbor']） |
| conandata.yml | 官方源 URL + SHA-256 |
| test_package/test.c | 消费者测试（真实 API 回环） |
| test_package/ohos_special_test.c | HarmonyOS 专项测试 |
| reports/test-report.md | 上游测试全量台账 |---

**编译结束**: 2026-09-01 18:11
**最终状态**: published
---

**编译结束**: 2026-09-01 19:21
**最终状态**: published
