# erkir 2.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（OHOS SDK llvm，arm64，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

上游 v2.1.1 是纯 CMake 工程：7 个翻译单元（`src/*.cpp`）、8 个公开头（`include/*.h`）、
`test/test.cpp` 一个测试源、零外部依赖。

**探索阶段（设备实测，源码目录 `$BUILD_SRC_DIR`）**

```bash
cmake -S "$BUILD_SRC_DIR" -B "$BUILD_SRC_DIR/build" \
      -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTING=ON -DCODE_COVERAGE=OFF
cmake --build "$BUILD_SRC_DIR/build" -j4
HOME="$TASK_DIR/test-home" ctest --test-dir "$BUILD_SRC_DIR/build" --output-on-failure
```

**配方路径（`conan create`，与 CI 同口径）**

```bash
conan create archives/e/erkir/2.1.1 \
      -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE"
```

配方要点：
- `generate()`：`BUILD_SHARED_LIBS=<shared 选项，默认 OFF>`、`ENABLE_TESTING=ON`、
  `CODE_COVERAGE=OFF`、`CMAKE_INSTALL_LIBDIR=lib`；
- `build()` 末尾 `cmake.test()` —— 层 1 上游测试（`docs/TEST_QUALITY_SPEC.md` §3.1）；
- `package()`：`cmake.install()` + 拷贝 `LICENSE` + `rmdir` 掉 `lib/cmake`（上游自带
  `erkirConfig.cmake`，会与 CMakeDeps 生成的配置撞名）与 `share/`（只装 README）；
- 层 2 `test_package/test_erkir.cpp`：消费者 18 条断言，期望值取自上游 `test/test.cpp`
  同一批数值（同 0.001 容差），`test()` 用 `self.run(..., env="conanrun")` 直跑。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake` 配置阶段直接 `FATAL_ERROR: Incorrect target architecture specified. It should be either x86 or x64` | 上游 `CMakeLists.txt` 的 `if (NOT MSVC)` 块默认 `TARGET_ARCH=x86` 并注入 `-m32`（x64 才是 `-m64`），arm64 不在白名单 | 补丁 `0001-CMakeLists.txt.patch` 把该块条件改为 `if (0)`（ConanCenterIndex 对同版本采用同样做法）；同块内的 `-Wall -Wextra -pedantic -Werror` 随之停用——clang 15 对这份 C++11 时代代码会报 `wstring_convert` deprecated 警告，`-Werror` 只会掩盖真正的可移植性信号 |
| 2 | 上游默认构建共享库（`option(BUILD_SHARED_LIBS ... ON)`） | 上游 option 默认值 | 配方按 `shared` 选项（默认 False）写 `tc.cache_variables["BUILD_SHARED_LIBS"]`，R26/R4 静态默认 |
| 3 | `ENABLE_TESTING=ON` 会连带默认打开 `CODE_COVERAGE`，注入 `--coverage` | 上游 `option(CODE_COVERAGE ... ON)` 只在 `ENABLE_TESTING` 分支内 | 配方显式 `CODE_COVERAGE=False`，不引入 coverage 运行时 |
| 4 | 手工直跑 `build/bin/unittest` 报 `Error relocating … symbol not found`（rc=127），而 `ctest` 正常 | 上游把 `liberkir.so` 以**相对路径** `../lib/liberkir.so` 记进 `DT_NEEDED`，动态解析相对 cwd（ctest 的 WORKING_DIR 恰为 `build/test`） | 配方默认静态链接，测试期不再依赖运行期路径；记录为「名字对、路径语义不对」的上游现象，未改上游测试 |
| 5 | `conan-init` 生成的 `conandata.yml` 是 `patches: {}` flow 形态，`refresh-patch --auto` 的自动登记被跳过（工具只在 `patches:` 缺失或块列表时追加） | 工具分支限制 | 人工按 CI L0f 要求写成块列表 `- patch_file: "patches/0001-…"` |
| 6 | CI 构建 #62527 被判「编译失败」：`make[2]: /bin/sh: Out of memory`、`/bin/sh: can't fork - try again` → `ellipsoidalpoint.cpp.obj Error 127` 与 `datum.cpp/cartesianpoint.cpp/coordinate.cpp Error 1` | Conan 的 CMake helper 无条件追加 `-j<tools.build:jobs>`，该 conf 缺省取 `os.cpu_count()`=20（本机 affinity 只有 8 ⇒ 2.5× 超订）；CI worker 内存受限窗口里 20 路并行 fork 失败——**源码与工具链本身没有错**（同一份源码设备侧 `-j20` 也通过过，属窗口相关的非确定性红） | 主配方在 `build()` 内、`cmake.build()` 之前 `self.conf.define("tools.build:jobs", 2)`（同族先例 `archives/l/libheif-openjpeg/1.23.0`、`archives/o/openjpeg2/2.5.4`、`archives/l/librtpi/1.0.0`）；`test_package` 用 `cmake.build(build_tool_args=["-j2"])` 钉最终并行度（仓库先例 argon2 / aria） |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`（+1/-1）：`if (NOT MSVC)` → `if (0)`，关闭
  x86/x64 专属架构块（`-m32`/`-m64` 注入与配置期 FATAL_ERROR，以及同块的 `-Werror`）。
- 上游测试源 `test/test.cpp`、`test/CMakeLists.txt` **零改动**（原始 tarball 逐字节一致）。

## 依赖版本

- 外部依赖：**无**（`requirements()` 为空；源码内无 `find_package`/`ExternalProject`/`FetchContent`）
- 系统库：`m`（`settings.os in ("Linux", "OHOS")`，R32）
- 工具链：clang/clang++ 15.0.4（OHOS SDK llvm）、CMake 4.1.2、Conan 2.29.1（OHOS 适配版）

## 验证结果

```bash
# 1) 探索构建 + 上游测试（沙箱 HOME）
HOME="$TASK_DIR/test-home" ctest --test-dir "$BUILD_SRC_DIR/build" --output-on-failure
#   1/1 Test #1: unittests ..... Passed
#   100% tests passed, 0 tests failed out of 1
#   逐字汇总行（ctest -V）：Total tests: 325, passed: 325, failed: 0

# 2) 配方全链（conan create：层1 上游 ctest + 层2 test_package）
conan create archives/e/erkir/2.1.1 -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE"
#   100% tests passed, 0 tests failed out of 1
#   ERKIR_TEST_PACKAGE_RESULT total=18 passed=18 failed=0
```

计数口径（R51 / AGENTS §3.5，四口径并列不混用）：
① 测试框架宏数——不适用（上游自带 `verify*` 断言函数，无 gtest/catch）；
② 源码断言调用点——106 处（`verifyDouble` 52 + `verifyString` 25 + `verifyPoint` 14 +
`verifyVector` 12 + 三元 `isValid` 断言 3）；
③ 框架注册数（ctest）——1（`add_test(NAME unittests)`）；
④ 运行期断言执行数——**325**（程序自报 `Total tests: 325`，循环内调用与
`verifyVector` 的三次 `verifyDouble` 展开使执行数大于调用点数）；
消费者断言（test_package）——18。

## 注意事项

- 上游 8 个 tag 与 `git ls-remote` 全量命中，`v2.1.1` tarball sha256
  `b314824c126bf933e2f08e5335e12b7ef3ded9ceb341d542276455d991e7e85d` 与 ConanCenterIndex
  配方登记值一致。
- 纯库包，按 R38/PF8 **不建** `commands.json`。
- 本包为平台新包（`archives/e/erkir` 在 `upstream/main` 不存在，`task_init --allow-unpublished`
  放行），按已知口径命中 PF9（包级 4 段文件 vs 5 段路径），在 PR 正文留痕后 `--no-preflight`。
