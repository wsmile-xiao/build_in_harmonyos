# copypp 0.3.0 适配笔记

## 编译环境
- 构建系统: cmake（`init-build` 按 URL 关键词猜成 `autotools`，以 `lang-preflight` 实测 `detected=cpp` 与源码事实纠偏为 cmake）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang++`，aarch64-unknown-linux-ohos）+ cmake 4.1.2 + conan 2.29.1
- 状态: built
- 交付形态: `package_type = "header-library"`（`implements = ["auto_header_only_mode"]`，package_id 单一）

## 编译步骤

```bash
conan create archives/c/copypp/0.3.0 \
  -pr:h=$HOST_PROFILE -pr:b=$HOST_PROFILE -c tools.build:jobs=4
```

- `generate()`：`CMakeDeps` + `CMakeToolchain`；注入
  `CMAKE_CXX_STANDARD=20`（上游头 `#error` 要求 C++20，conan profile 面是 17）、
  `COPYPP_TEST=ON`（**上游 CI 显式传 OFF**，本适配必须开）、
  `GTest_DIR`/`fmt_DIR`（指向 Conan 包自带的上游 CMake config）、
  `CMAKE_PROJECT_INCLUDE`（生成 `copypp-upstream-includes.cmake`，注入 fmt/nlohmann_json 头目录 + `-UNDEBUG`）。
- `build()`：`cmake.configure()` → `cmake.build()` → 逐一执行 `test/` 下 7 个 gtest 二进制，
  解析 `[==========] N tests ... ran.` 与 `[  PASSED  ] N tests.` 汇总行计数，任一非零即抛异常让构建失败；
  同时输出机器可读行 `HMBS_UPSTREAM_TEST_RESULT={...}` 与源码宏清点数（候选数法两口径）。
- `package()`：`copy("*.hh", include/ → include/)` + `copy("LICENSE*", → licenses/)`（header-only，无 install 步骤依赖）。
- `test_package/`：消费者 `test_copypp` 针对**已安装包头**执行 17 个显式检查（不依赖 assert/NDEBUG）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(GTest CONFIG REQUIRED)` 找到配置后 `GTest::gtest`/`GTest::gtest_main` 目标不存在 | Conan CMakeDeps 生成的 `gtest-config.cmake` 只声明 `gtest::gtest`（ohpcd 的 gtest recipe `cmake_file_name="gtest"`、无组件拆分），而上游测试树写的是 `GTest::gtest_main` | `GTest_DIR` 指向 gtest 包**自带**的 `lib/cmake/GTest/GTestConfig.cmake`（上游 gtest 安装件，含 gtest/gtest_main 两个目标）；同法 `fmt_DIR` → `lib/cmake/fmt/fmt-config.cmake` 才有 `fmt::fmt-header-only`（CMakeDeps 版只有 `fmt::fmt`） |
| 2 | `'fmt/core.h' file not found`（`copypp_test3`）、`nlohmann/json.hpp` 无处可寻 | 上游 `test/CMakeLists.txt` 只给**部分**目标链接 fmt，nlohmann_json 则被 3 个测试 include 却**无任何目标链接**——上游是在 `/usr/include` 系统头齐备的机器上写的；设备上这些头只在 conan 包内 | 按 CMake 官方「Code Injection」机制 `CMAKE_PROJECT_INCLUDE` 在根工程作用域 `include_directories(<fmt/include> <nlohmann_json/include>)`，等价于系统 include 路径；**上游文件零改动、零补丁** |
| 3 | Release 默认 `-DNDEBUG` 把 `copypp_test`/`copypp_test2` 的 `assert()` 检查点编译成空转（两文件 0 个 gtest EXPECT/ASSERT 宏） | 上游用 C `assert()` 做断言，而上游 CI 用 Release 且 `-DCOPYPP_TEST=OFF` 根本不跑测试 | 同一注入文件里 `add_compile_options(-UNDEBUG)` 让断言真实生效（该方向只会暴露更多失败，不会减少失败）；实测开启后 33/33 全过 |
| 4 | `init-build` 把 `BUILD_SYSTEM` 猜成 `autotools` 并生成空模板占位 | `init_build.py::_guess_build_system()` 只按 URL 关键词猜 | 以源码事实（`CMakeLists.txt` + `lang-preflight detected=cpp`）为准手写 CMake 配方；`manifest.yaml` 两处 `build_system`/`build.system` 钉 `cmake` |
| 5 | 上游根 CMake `if (NOT DEFINED COPYPP_TEST) set(COPYPP_TEST "build mathpp tests" ON)` 把变量置成列表 | 上游笔误（`set` 的多值形式），但值非假常量 → `if` 仍为真 | 不动上游；配方显式 `-DCOPYPP_TEST=ON` 让语义确定 |

## 源码修改

无（零补丁：上游源码、测试用例、CMake 脚本一字未改；`patches_applied: []`）。
构建接线全部发生在配方侧（CMake 注入点 + Conan 依赖目录），不落任何上游文件。

## 依赖版本

- 交付运行依赖：**零**（header-only，纯 C++20 标准库；W0 `conan list -r=ohpcd` 三味实核）
- 构建/测试期依赖（`test_requires`，不传播给消费者）：`gtest/1.17.0`、`fmt/11.1.3`、`nlohmann_json/3.12.0`（均在 ohpcd 制品仓有可得配方/二进制）

## 验证结果

```bash
# ① 本地 conan create（配方自包含 + 上游 7 目标 33 用例 + test_package 17 检查）
#   → rc=0；HMBS_UPSTREAM_TEST_RESULT={"...","executed":33,"passed":33,"failed":0,...}
#   → copypp consumer checks: 17 run, 0 failed

# ② 沙箱 HOME 下原生跑上游套件（HOME="$TASK_DIR/test-home" 字面执行）
#   → 见 reports/test-report.md 与 $TASK_DIR/evidence/

# ③ 采信轮（清缓存后干净构建）
sh tools/conan_verify_round.sh copypp 0.3.0 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
#   → 见 reports/conan-verify-report.md 与 evidence-index.json
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/icurve/copypp.hh` / `copypp_only.hh` / `meta.hh` | 上游三个公开头（打包内容与 tarball 源逐字节一致，sha256 复核见 `reports/conan-verify-supplement.md`） |
| `licenses/LICENSE` | MIT 许可证 |
| `conaninfo.txt` / `conanmanifest.txt` | Conan 打包清单 |

> 不交付上游 `lib/cmake/copypp/*.cmake` 安装件：header-only 消费方由 Conan `CMakeDeps`
> 按 `package_info()` 生成 `copypp-config.cmake`（目标 `icurve::copypp`），与
> conan-center-index 的 copypp 配方口径一致（CCI 亦只 `copy()` LICENSE + `*.hh`）。
> 实测包目录（`conan cache path "copypp/0.3.0@ohpcd/stable:<pid>"`）只含
> `include/icurve/*.hh` + `licenses/LICENSE` 两个业务目录。

## 注意事项

- **tag 精确匹配**：远端 `refs/tags/v0.3.0` 与 `refs/tags/v0.3.0-pre` 指向同一提交
  `d017573496dfe8c0dc4bc5ba1ef551d4ad290031`，取源必须用精确 ref，禁止前缀模糊匹配。
- header-only 形态下 conan-verify 的 G4/L2/L4/L5 走「跳过分支并列打 ✅」，
  该四项自动读数不单独采信，人工补测见 `reports/conan-verify-supplement.md`。

## 编译结束

最终状态: built（conan-verify 通过，未向制品仓 upload）
