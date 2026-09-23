# DRAFT: 上游 CMake 用 include(Catch)/catch_discover_tests 时，header-only catch2 包缺 CTest 集成模块 — 注入最小 Catch.cmake

> 来源: ctpg 1.3.7 HarmonyOS PC 适配（header-only 单头文件编译期解析器生成库）
> 状态: 草稿 (draft) — 与 DRAFT-ctpg-1.3.7-catch2-ctest-module-injection.kv 配对
> 关联: archives/c/ctpg/1.3.7/reports/knowledge-candidate-ledger.md (C1)

## 问题

ctpg 1.3.7 上游 `CMakeLists.txt` 的测试分支（`CTPG_ENABLE_TESTS=ON`）写法：

```cmake
find_package(Catch2 2 REQUIRED)
add_executable(testbin tests/main.cpp tests/regex_tests_1.cpp ...)
target_link_libraries(testbin PRIVATE Catch2::Catch2 ctpg::ctpg)
include(Catch)
catch_discover_tests(testbin)
```

`conan create`（ohos-aarch64 profile）时：

```
CMake Error at CMakeLists.txt:71 (include):
  include could not find requested file: Catch
CMake Error at CMakeLists.txt:72 (catch_discover_tests):
  Unknown CMake command "catch_discover_tests".
```

注意：`find_package(Catch2 2 REQUIRED)` 已经命中（CMakeDeps 生成了
Catch2Config.cmake 与 Catch2::Catch2 target），失败发生在随后的
`include(Catch)`——Catch2 2.x 的 ctest 用例注册宏
`catch_discover_tests` 由随框架安装的 contrib 模块 `Catch.cmake` 提供。

## 根因

- Catch2 2.x 的 `catch_discover_tests` 宏在框架安装目录的 contrib 模块
  （`Catch.cmake`）中，不随 `single_include` 头文件打包；
- ohpcd 制品仓的 `catch2/2.13.10-r0` 配方按 header-library 最小打包只复制
  `single_include/catch2` 头文件与 LICENSE，**不含** Catch.cmake/contrib 模块；
- 因此"测试框架包已发布、find_package 可命中"与"CTest 集成模块缺失"同时成立，
  配置期直接崩溃——不是当前库源码缺陷，是打包完整性问题。

## 方案

conanfile.py `generate()` 中（`can_run(self)` 时）注入最小 Catch.cmake：

```python
mod_dir = os.path.join(self.build_folder, "cmake-modules")
os.makedirs(mod_dir, exist_ok=True)
with open(os.path.join(mod_dir, "Catch.cmake"), "w") as f:
    f.write(
        "# Minimal Catch.cmake for ctpg upstream ctest integration\n"
        "function(catch_discover_tests TARGET)\n"
        "    add_test(NAME ${TARGET} COMMAND ${TARGET})\n"
        "endfunction()\n"
    )
tc.variables["CMAKE_MODULE_PATH"] = mod_dir
```

关键点：

1. `generators = "CMakeDeps"` — 让 `find_package(Catch2 2 REQUIRED)` 命中制品仓包；
2. `requirements()` 中 `can_run(self)` 时才 `requires("catch2/2.13.10-r0")`
   — header-only 包本体零依赖，测试框架只进本机构建；
3. 最小 `Catch.cmake` 把 `catch_discover_tests(testbin)` 注册为单个 ctest 用例
   — testbin 内包含上游全部 52 个 TEST_CASE，运行即全执行；
4. 不改上游源码、不产生补丁 diff；`build()` 中 `cmake.configure/build/test`
   正常驱动上游测试（R51 如实回填 52/52）。

## 验证

- `conan-verify ctpg 1.3.7`：G1/G0/G2/G3/G4/L2/L4/L5 全 PASS；
- testbin 实跑：`All tests passed (319 assertions in 52 test cases)`，exit 0；
- W3 本地 CI 模拟（zsh build_and_test.sh）：Success 1/1，Pass rate 100%，
  L0/L1/L4 全 pass，L1e 破坏性反向验证通过（test 真实依赖 ctpg）。

## 适用边界 / 反例

- 适用：上游 CMakeLists 用 `find_package(Catch2 2 REQUIRED)` + `include(Catch)`
  + `catch_discover_tests` 的库；制品仓 catch2 包不含 contrib 模块时。
- 反例：
  - 上游用 `FetchContent_Declare(Catch2 ...)` — 走既有草稿
    `DRAFT-cmake-test-framework-fetch-to-conan-find-package`（find_package 转换）；
  - 上游以 git submodule vendoring Catch2（release tarball 空目录）— 走
    `DRAFT-kangaru-4.3.2-catch2-submodule-test-requires`（test_requires +
    CMakeDeps 生成 Catch2Config，不触发 include(Catch) 缺失）。