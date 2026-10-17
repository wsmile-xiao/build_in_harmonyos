# merve 1.2.2 适配笔记（任务 #8811 / 主活动）

## 上游身份

- 仓库 `https://github.com/nodejs/merve`，tag `v1.2.2`，release/归档 tarball
  `https://github.com/nodejs/merve/archive/refs/tags/v1.2.2.tar.gz`，
  sha256 `8f19c2132447b9113545ffd399cb2bc1e61c6166743921b04883f8e1d778d69e`（68511 B）。
- 本机对两个独立入口分别取数对拍：`codeload.github.com/.../refs/tags/v1.2.2` 与
  `github.com/.../archive/refs/tags/v1.2.2.tar.gz` 字节相同、同 sha256，
  故 `conandata.yml` 写 codeload 在前的双源 list（真机 github 直连常超时，CI 走规范 URL）。
- 任务表 `url` 为空，上表地址由 Homebrew formula `merve` 的 `urls.stable` 反查并实取校验。
- 版本号 `1.2.2` 与 `CMakeLists.txt` 的 `VERSION 1.2.2`、`include/merve/version.h` 的
  `MERVE_VERSION "1.2.2"` 三处一致，无 `-git<sha>` 之类需还原的后缀。

## 问题 1：上游只在“自己用 CPM 抓 GTest”的分支里找 git，Conan 提供 GTest 时测试被静默关闭

`CMakeLists.txt` 的顺序是：

```cmake
find_package(GTest QUIET)
if(NOT GTest_FOUND)
  include(cmake/CPM.cmake)
  find_package(Git QUIET)          # ← 只有这条分支会探测 git
  ...CPMAddPackage(googletest)...
endif()
...
if (MERVE_TESTING AND NOT EMSCRIPTEN)
  if(Git_FOUND)                    # ← 但测试目录的门禁又只看 Git_FOUND
    add_subdirectory(tests)
```

用 `test_requires("gtest/1.17.0")` + `GTest_DIR` 指到 Conan 包时 `find_package(GTest)` 直接命中，
`find_package(Git)` 根本不会执行 → `Git_FOUND` 为假 → 配置期打印
`The tests are disabled because git was not found.`、`tests/` 不加入构建，
`ctest -N` 枚举 0 项。构建与打包仍全部成功，属于**假绿**风险。

修法：`patches/0001-tests-when-gtest-provided.patch` 把门禁放宽为
`if(Git_FOUND OR GTest_FOUND)`（git 只是 CPM 抓 GTest 的手段，GTest 已在场就不需要它）。
另外配方在 `build()` 里加了硬校验：`ctest -N` 枚举 < 100 项直接 `ConanException` 失败，
不再可能“没跑上游测试却出包”。实测第一轮正是这条守卫把该问题暴露出来的。

## 问题 2：`ctest -N` 与汇总行的取数口径

- `ctest -N` 的行是 `  Test   #1: real_world_tests.esbuild_hint_style`（**行首两个空格**，
  编号按宽度对齐），`line.startswith("Test #")` 恒假 → 必须用正则 `^\s*Test\s+#\d+:`。
- 零失败时 CTest 汇总行是 `100% tests passed out of 101`，**不含** `tests failed` 字样，
  按汇总句解析会算出 0 项。改为按逐项结果行 `^\s*\d+/\d+\s+Test\s+#\d+:` 计数，
  以 ` Passed` 判定通过，独立于汇总句措辞。

## 问题 3：其它真机噪声（不影响结果，记录以免重复排查）

- `cmake` 提示 `Standard CMAKE_CXX_STANDARD value defined in conan_toolchain.cmake to 17 has
  been modified to 20 by cmake/lexer-flags.cmake`：上游用无条件 `set(CMAKE_CXX_STANDARD 20)`
  覆盖缓存值，配方不与其争；OHOS SDK clang 23.1.1 支持 C++20，实测编译通过。
- `Problem parsing /proc/meminfo`（cmake 4.4.3 读不到 OHOS 的 meminfo）、
  `gmake: jobserver mkfifo: .../GMfifo#### Operation not permitted`（HMDFS 不允许建 fifo，
  gmake 退回非并行 jobserver）均为无害告警。
- 真机 `conan create` 的 `PATH` 里没有 git 也不影响本配方（补丁后测试不再依赖 `Git_FOUND`）。

## 依赖与产物

- 外部依赖 0 个：`MERVE_USE_SIMDUTF` 默认 OFF（ simdutf 只是可选加速），
  `MERVE_BENCHMARKS` 关闭，测试框架 `gtest/1.17.0` 走 `test_requires`（制品仓已发布）。
- 产物 `libmerve.a` + 头文件 + `merve-config.cmake` + `merve.pc` + licenses，
  **无 `bin/`** → 不触发 L0k/R38 的 `commands.json` 要求。

## 真机验证

`CONAN_HOME=~/work/psj/ch-mv8811`（只留 `ohpcd` remote）、profile `ohos-aarch64`，
`conan create archives/m/merve/1.2.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
→ `CREATE_EXIT:0`；`HMOS_UPSTREAM_TEST_RESULT` 记 `configured=101, passed=101, failed=0`，
ctest 汇总 `100% tests passed out of 101`、逐项 ` Passed` 计数 101；
消费者 `test_package` 43/43、`harmonyos_test` 29/29。详见 `reports/test-report.md`。
