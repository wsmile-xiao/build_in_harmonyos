# ctml 2.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMakeLists.txt`，交付物仍为 header-only）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，libc++）
- 设备: HarmonyOS PC aarch64，conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 软件概览

CTML（github.com/tinfoilboy/CTML）是纯头文件 C++11 HTML 文档构造库：
单头 `include/ctml.hpp`（1542 行），`CTML::Node` / `CTML::Document` 两个主类，
上游 `CMakeLists.txt` 只声明 `add_library(CTML INTERFACE)`，**0 外部依赖**。

## W0 立项预检（三关全过）

| 关 | 判据 | 实测读数 |
|---|---|---|
| W0-1 版本可得性 | `git ls-remote --tags https://github.com/tinfoilboy/CTML.git` | 5 个 tag 全量命中：1.0.0 / 1.0.1 / 1.1.0 / 1.1.1 / **2.0.0 = 8076165596e30fdba274297b9b53a8007c0a74c0**；tag 归档 URL 可下载（113703 字节） |
| W0-1 源 sha256 同源 | 本地下载实测 vs CCI | `e13b3bb04903f47b90b286f8a4695232179e28474a0a33f1a3f333552338d132` == CCI `recipes/ctml/all/conandata.yml` 的 "2.0.0" 条目（三路一致） |
| W0-2 硬依赖 | 配方 `requires`/`build_requirements` 双零 + 上游 CMakeLists 无 `find_package`/外部 `target_link_libraries`；`conan list ctml/* -r=ohpcd` = 0（本包为新包，无既有副本） | 0 依赖，无缺失硬依赖 |
| W0-3 平台不可移植 | `grep -rniE 'altivec\|mmx\|emmintrin\|xmmintrin\|3dnow\|immintrin\|arm_neon'`（源码树，`*.hpp/*.h/*.cpp/*.c/CMakeLists.txt`）| **rc=1 零命中**（唯一 `__i386\|__x86_64` 命中在 vendored `tests/catch.hpp:5470` 的 `#if defined(...)` 分支内，带 `#else raise(SIGTRAP)` 通用回退，aarch64 走死分支 → 注释/死块档，直过） |
| W0-3 glibc printf 钩子 | `grep -rniE 'printf\.h\|register_printf'` | **rc=1 零命中** |

## 编译步骤

配方 `conanfile.py` 的 `generate()` → `build()`（层 1 上游测试在内）：

```bash
# conan create 内部等价步骤（CMakeToolchain 注入）
cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release \
      -DCTML_TESTS_ENABLE=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build <build>            # 编译上游 CTMLTest（Catch2 v2 单头 ×2 个测试 TU）
ctest --test-dir <build> --output-on-failure   # 上游官方测试（cmake.test()）
# package(): 只拷贝 include/ctml.hpp + LICENSE（header-library，package_id 清空）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake -S . -B build` 直接失败：`Compatibility with CMake < 3.5 has been removed from CMake` | 上游写死 `cmake_minimum_required(VERSION 3.0)`，设备 CMake 4.1.2（CI 同族）已移除 <3.5 兼容 | 传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（**必须用 `tc.cache_variables`**：`tc.variables` 写进 toolchain 文件、在 `cmake_minimum_required()` 之后加载不生效——既有条目 E187 / DRAFT-E321 的结论）。不改上游源码、不打补丁 |
| 2 | `conan-init` 按 `BUILD_SYSTEM=autotools` 生成了 autotools 模板（init-build 的构建系统探测把本包判成 autotools） | 源树只有 CMakeLists.txt，探测器回退默认值 | 手写配方改走 CMake 路径，`manifest.yaml` 的 `build.system` 显式钉 `cmake` |
| 3 | `make: jobserver mkfifo: ... Operation not permitted` | 设备 SELinux/HMMAC 拒绝 FIFO 文件，make 4.4.1 自动退化 pipe jobserver，**并发未退化**（device-facts §一.13） | 噪声，不处理；`tools/make_jobserver.sh` 已注入 `MAKEFLAGS=--jobserver-style=pipe` |
| 4 | test_package 首版多行格式化期望与实物不符 | `AppendNodeToHead(title)` 后 `<title>` 在 MULTIPLE_LINES 下的缩进由上游渲染器决定，上游测试未覆盖该形态 | 消费者测试改为「flat 模式断言 `<title>ctml</title>` 存在」+「多行断言用与上游 behavior_tests 逐字相同的期望字符串」，不臆造期望值 |

## 源码修改

**无（零补丁）**：`patches: {}`，`manifest.patches_applied: []`。唯一的平台差异用 configure 选项解决（见问题 1）。

## 依赖版本

0 运行依赖、0 编译期工具依赖（不需 `tool_requires`：上游带 CMakeLists.txt，设备/CI 均有 cmake）。

## 上游测试清点（R51 三步法·申报表）

上游测试树：`tests/behavior_tests.cpp`（1 TEST_CASE / 19 SECTION / 21 REQUIRE）、
`tests/construction_tests.cpp`（1 TEST_CASE / 5 SECTION / 5 REQUIRE）、`tests/catch.hpp`
（Catch2 v2 单头）；入口 `CMakeLists.txt` 的 `enable_testing()` + `add_test(NAME CTMLTests)`。

| 口径 | 取数命令 | 值 |
|---|---|---|
| 源码宏数（TEST_CASE） | `grep -c 'TEST_CASE(' tests/*.cpp` | 2（1+1） |
| 源码分支（SECTION，附注） | `grep -c 'SECTION(' tests/*.cpp` | 24（19+5） |
| 框架注册数（Catch2） | `./CTMLTest --list-test-names-only \| wc -l` | 2 |
| 框架注册数（CTest） | `ctest -N` | 1 |
| 运行期报告 | `./CTMLTest` → `All tests passed (26 assertions in 2 test cases)` | 26 断言 / 2 case |
| 源码断言词面 | `grep -c 'REQUIRE(' tests/*.cpp` → 21+5；`CHECK(` → 0 | 26 |
| **N（断言口径，取候选最大）** | max(源码 26, 运行期 26) | **26** |

差额归因：2 个 TEST_CASE 按 SECTION 展开为 24 次分支执行，落成 26 条 REQUIRE 断言；
其余口径（2 case / 24 section / 1 ctest 项）**全部 ≤ 26**，不存在少报方向的差额。
N′（本次实跑）= 26，PASS=26 / FAIL=0 / SKIP=0 / NOT_RUN=0，TOTAL=PASS+FAIL+SKIP+NOT_RUN=26。

**鸿蒙特有测试（不进上游分母）**：`test_package/test.cpp` 消费者断言 30 条
（运行期 `CTML-CONSUMER checks=30 failures=0`）。

## 验证结果

```bash
# ① 上游测试（沙箱 HOME，device-facts §一.11；原始输出 $TASK_DIR/upstream-test/run.log，2026-09-26T08:59:15Z）
HOME="$TASK_DIR/test-home" ctest --test-dir <build> -N                     # Total Tests: 1  rc=0（N>0，非 ctest 空跑）
HOME="$TASK_DIR/test-home" ctest --test-dir <build> --output-on-failure    # 1/1 Passed, 100% tests passed  rc=0
HOME="$TASK_DIR/test-home" ./CTMLTest                                      # All tests passed (26 assertions in 2 test cases)  rc=0
HOME="$TASK_DIR/test-home" ./CTMLTest --list-test-names-only | wc -l       # 2（list 模式 rc=2 = Catch2 NO_TESTS，非测试失败）

# ② 消费者测试（test_package，安装包视角；采信轮干净轮 reports/conan-create.log 尾部原文）
RUN: ./test_ctml                                                           # CTML-CONSUMER checks=30 failures=0  rc=0

# ③ 采信轮 tools/conan_verify_round.sh ctml 2.0.0 → rc=0（干净轮）
#    干净轮判读 run_make=6 / calling_build=2 / apply_patch=0 → verdict=clean
#    门禁 G1/G0/G2/G3/G4/L5 PASS；L2/L4 SKIP（header-only）→ 已人工补测 reports/conan-verify-supplement.md
#    证据副本 $TASK_DIR/evidence-43a305a/conan-create.log（12345B, sha256 4efbc56b…）
#                          …/conan-verify-report.md（1854B, sha256 12d4023e…）

# ④ 四步收尾序（AGENTS §3.3）
#    finish … built → finish_restore.sh --apply → capture_evidence.py --verify → 必要时 --restore 复跑至 rc=0
#    实测 rc：finish(首跑)=1（失败步骤 step8：缺 reports/test-report.md）→ 补齐 test-report.md 后 finish(复跑)=0
#             finish_restore.sh --apply=0（还原 SUMMARY.md + 镜像改写的 conandata.yml；保留本 notes.md 有意编辑）
#             capture_evidence.py --verify=1（报告改写史 2 项）→ 按结论行 --restore <index>=0 → 复跑 --verify=0 ✅
```

### 对话 #1（2026-09-26，适配会话）

- **configure 参数**（采信轮干净轮原文）：`cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=<generators>/conan_toolchain.cmake -DCTML_TESTS_ENABLE="ON" -DCMAKE_POLICY_VERSION_MINIMUM="3.5" -DCMAKE_BUILD_TYPE="Release"`
- **耗时**：W0 + 配方适配约 25min；采信轮（清缓存 → conan create → 证据副本 → 快照）约 6min；finish 约 5min；上游/消费者测试复跑 <1s。
- **编译结果**：conan create rc=0；`package(): Packaged 1 '.hpp' file: ctml.hpp` + `LICENSE`；`1/1 Test #1: CTMLTests ... Passed`；`CTML-CONSUMER checks=30 failures=0`。
- **遇到的问题与解决**：CMake 4.x 拒绝 `cmake_minimum_required(VERSION 3.0)` → `cache_variables` 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（零补丁，E187）；init-build 把构建系统误判为 autotools → 手写 CMake 配方并把 `manifest.build.system` 钉 `cmake`；header-only 使 L2/L4 跳过 → `reports/conan-verify-supplement.md` 人工补测；finish 内嵌 G0 报「安装产物为空」为预期（上游无 `install()` 规则）。

## 注意事项

- 上游 `CMakeLists.txt` 的测试目标带 `-D_GLIBCXX_DEBUG -g`：本环境为 libc++，该宏为
  libstdc++ 专属调试开关，在 libc++ 下是惰性宏定义，不影响测试语义（实测 26/26 通过）。
- `README.md` 的 Tests 一节写的 `tests/tests.cpp` 与实物不符（实物是 `behavior_tests.cpp`
  + `construction_tests.cpp`），以 `CMakeLists.txt` 为准；属上游文档陈旧，未改动源码。
- 本包为**全新包**（`archives/c/ctml` 在 upstream/main 不存在），`task_init.sh` 加
  `--allow-unpublished` 放行；分支名 `feat/ctml-2.0.0` == `ctml-2.0.0`，过 CI 分支名门禁。
