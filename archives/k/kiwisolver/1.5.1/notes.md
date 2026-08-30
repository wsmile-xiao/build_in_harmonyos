# kiwisolver 1.5.1 适配笔记

## 编译环境
- **构建系统**: cmake（header-only INTERFACE 库 kiwi::kiwi，无 install() 规则）
- **编译日期**: 2026-08-30
- **编译器**: clang（OHOS 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁，纯标准 C++11 header-only）

## 编译步骤（conan create 全流程）

```bash
conan create archives/k/kiwisolver/1.5.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的官方 GitHub tag 归档下载并 strip_root（目录 kiwi-1.5.1）。

### 2. 打包（package()）
- 上游是 header-only 库（`add_library(kiwi INTERFACE)`），CMakeLists.txt **无 install() 规则**
- package_type=header-library，`package()` 手动拷贝 `kiwi/*.h`（17 个头文件）到 `include/kiwi/`
- package_info()：header-only（无 libs/libdirs/bindirs）

## 上游测试（rule 4 全量核验）
- 测试目录：`tests/`，7 个 googletest 测试文件（googletest v1.16.0，FetchContent 拉取）
  - ConstraintTest 5 + ExpressionTest 7 + SimplexTest 1 + SolverTest 9 +
    StrengthTest 2 + TermTest 7 + VariableTest 7 = **38 个 TEST 用例**
- 运行方式：CMake `KIWI_BUILD_TESTS=ON` → add_subdirectory(tests) →
  `gtest_discover_tests(kiwi_tests)`（googletest 框架）
- 适配后：test_package 编译消费者程序，真实调用 `kiwi::Solver` API（R34）
  ——求解 x+y=10、x-y=4 → x=7, y=3，断言求解结果

## 已知限制
- header-only 库，无编译产物；test_package 通过编译+运行消费者程序验证
- 上游 Python 绑定（py/ 目录）不在本次适配范围（仅 C++ 库）
