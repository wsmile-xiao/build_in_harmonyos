# rang 3.3 适配笔记

## 编译环境
- 构建系统: cmake (header-only, INTERFACE)
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4 (target aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

rang 为 header-only 单头文件库（include/rang.hpp），无 configure/make 步骤：

1. `conan create archives/r/rang/3.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`
2. 主包：下载官方 v3.3 tarball（SHA-256 e835f79e...），拷贝 include/rang.hpp + LICENSE。
3. test_package：CMake consumer，find_package(rang) + rang::rang，编译并运行
   test_rang（消费者验证）与 ohos_platform_test（鸿蒙平台专项）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create: test_package 报 `settings.os.version` value not defined | OHOS profile 带 os.version，test_package 未声明 | `configure()` 中 `self.settings.rm_safe("os.version")`（仓库 mdurl/afdko 范式） |
| 2 | test_package 编译失败：`clang-15: error: invalid library name in argument '-stdlib=libstdc++'` | OHOS clang 15 仅提供 libc++；conan CMakeToolchain 在 OHOS 下错误生成 -stdlib=libstdc++ | test_package `generate()` 显式 `tc.extra_cxxflags.append("-stdlib=libc++")` 并映射 CMAKE_SYSTEM_NAME=Linux / CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 3 | 鸿蒙专项测试初版校验 OS_LINUX 恒失败 | rang.hpp 在文件末尾 `#undef OS_LINUX/OS_WIN/OS_MAC`（内部宏不污染用户代码，设计行为） | 测试改校验编译器平台宏 `__OHOS__`/`__unix__`/`__linux__`，并保留真实行为断言（Auto/Force/Off 输出） |

## 源码修改

无（header-only，未打补丁；patches/ 为空）。

## 依赖版本

- 无运行时依赖（header-only）。
- 测试框架：doctest 2.5.2（仅上游 test/test.cpp 的 6 个 TEST_CASE 使用，来自 ohpcd 制品仓 conan 包）。

## 验证结果

```bash
conan create archives/r/rang/3.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...   # EXIT 0
# test_package: test_rang  -> All rang consumer tests passed!
# test_package: ohos_platform_test -> platform: OHOS / All HarmonyOS platform tests passed! (EXIT 0)
# 上游 6 个 TEST_CASE: 6/6 passed, 21/21 assertions (详见 reports/test-ledger.md)
```

## 注意事项

- OS_LINUX/OS_WIN/OS_MAC 是 rang.hpp 内部宏，文件末尾会被 #undef，消费方不应依赖。
- 下游 find_package(rang) + target_link_libraries(... rang::rang) 即可。
---

**编译结束**: 2026-09-02 02:20
**最终状态**: built
