# 测试报告 — cpplocate 2.3.0

> **项目**: cpplocate 2.3.0（C++ Locator Library）
> **测试日期**: 2026-09-02
> **测试环境**: HarmonyOS HongMeng Kernel aarch64（OHOS userland, clang 15.0.4）
> **测试类型**: 官方测试套件（googletest/gmock 1.17.0）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 51 | 100% |
| 通过 (PASS) | 51 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

（独立上游 TEST 用例口径：liblocate_test 21 + utils_test 20 + cpplocate_test 10 = 51/51）

## 二、测试结论

### 2.1 总体评价

✅ **cpplocate 2.3.0 在 HarmonyOS PC (aarch64) 上全部上游测试通过。**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无阻塞问题 | — | — |

### 2.3 可用功能清单

```
✅ 可执行路径定位 getExecutablePath / getModulePath
✅ 库路径定位 getLibraryPath / locatePath
✅ 平台约定 pathSeparator / libPrefix / libExtension / libExtensions
✅ 用户目录 homeDir / profileDir / documentDir
✅ 应用目录 configDir / roamingDir / localDir / tempDir
```

### 2.4 已知限制

1. 上游测试需 gtest 1.17.0（要求 C++17）；库本体保持 C++11 兼容
2. `homeDir` 在 OHOS 上返回 `getpwuid` 主目录（本环境为 /storage/Users/currentUser）

## 三、测试执行记录

### 3.1 上游测试（51 个独立 TEST）

| 测试程序 | 套件 | 用例数 | 结果 |
|----------|------|:----:|:----:|
| liblocate-test | liblocate_test | 21 | ✅ 21/21 |
| liblocate-test | utils_test | 20 | ✅ 20/20 |
| cpplocate-test | cpplocate_test | 10 | ✅ 10/10 |

### 3.2 运行时环境说明

- 测试二进制以 `../../../liblocate.so` 相对 NEEDED 链接，需从对应子目录运行并注入
  `LD_LIBRARY_PATH=<build-native>`（上游 CMake 输出目录约定）。

## 四、HarmonyOS 专项测试

- `test_package/test_cpplocate_hmos.cpp`：编译并运行通过，全部断言
  `ALL_CPPLOCATE_HMOS_ASSERTIONS_PASSED`，exit 0。
- `test_package/test_cpplocate.cpp`：消费者视角验证（路径解析 + 平台约定），
  `test_cpplocate: OK`。

## 五、日志与哈希

| 日志 | 绝对路径 | SHA-256 |
|------|----------|---------|
| liblocate-test | /storage/Users/currentUser/junshi_liu/build_in_harmonyos/.oh-executor/cpplocate-2.3.0-r01-liblocate-test.log | b80dad67dd9fba6d027f2bf9e8df2e57f05938d12bdbbe681904efc3c9ba38f1 |
| cpplocate-test | /storage/Users/currentUser/junshi_liu/build_in_harmonyos/.oh-executor/cpplocate-2.3.0-r01-cpplocate-test.log | 12d27a1b208e7fa1c632cbc0607591471df2d490c592814f1ef0cd960933c441 |
