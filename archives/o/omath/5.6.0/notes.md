# omath 5.6.0 适配笔记

## 编译环境

- 构建系统: cmake（上游 `cmake_minimum_required(3.26)`，设备 CMake 4.1.2）
- 编译日期: 2026-09-26
- 编译器: **clang/clang++ 22.1.8**（ohpcd 制品仓 `clang/22.1.8`，经 `tool_requires` 接入；
  设备/CI 自带的 SDK clang 15.0.4 不可用，理由见下）
- C++ 标准库: SDK 自带 libcxx-ohos 15.0.4（`_LIBCPP_VERSION 15004`，与 CI worker 同一份）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 编译步骤

1. 源码：`conandata.yml` 指向官方 tag archive
   `https://github.com/orange-cpp/omath/archive/refs/tags/v5.6.0.tar.gz`，
   sha256 `9ddd9ae712b0d2edd46bb161043825a850211a85dcc5a8c284718a6e02f59f66`
   （与任务卡 CCI 读数逐字一致；解包 441 文件 / 5.7MB）。
2. 采信轮固序命令（含清缓存四步 + 证据三份 + finish 前快照）：
   ```bash
   sh $HOME/ws/tools/conan_verify_round.sh omath 5.6.0 \
     --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
   ```
   等价的单条配方构建：
   ```bash
   conan create $TARGET_REPO/archives/o/omath/5.6.0 \
     -pr:h=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 \
     -pr:b=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 --build=missing
   ```
3. 配方注入的构建选项：`OMATH_BUILD_TESTS=ON`、`OMATH_USE_AVX2=OFF`、
   `OMATH_BUILD_BENCHMARK/EXAMPLES/ENABLE_LUA/ENABLE_HOOKING/IMGUI_INTEGRATION/ENABLE_MODULES=OFF`。
4. `build()` 内执行 `ctest --test-dir tests --output-on-failure --no-tests=error`（上游单测全量）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `omath::Angle<float, …>` 连默认实参都无法实例化：`sorry, non-type template argument of type 'float' is not yet supported` | OHOS SDK clang 15.0.4 未实现 C++20 浮点非类型模板参数（`-std=c++20`/`c++2b`/`gnu++2b`/`-fexperimental-new-constant-interpreter` 四种姿势实测同错），而 Angle 的 `Min/Max` 就是浮点 NTTP | `build_requirements()` 加 `tool_requires("clang/22.1.8")`，在 `generate()` 里 `self.conf.update("tools.build:compiler_executables", …)` 覆盖 profile 指向的 SDK clang15。clang22 实测可编译/链接/运行 Angle；libc++ 仍是 SDK 15.0.4（同 worker 一致） |
| 2 | 全量测试 TU 扫描 ~70/78 失败：`missing 'typename' prior to dependent type name`（P0634）、`static_assert(false)`（P2593）等 7 类 | 同上，属编译器语言特性缺口，不是源码缺陷 | 同 #1，换编译器后 `tests/engines` 12/12、`tests/general` 全部 TU 语法通过（`OMATH_BUILD_TESTS` 需同时定义，否则上游 `#ifdef OMATH_BUILD_TESTS` 的 friend 声明不生效会误报 private 访问） |
| 3 | `#include <expected>` / `<print>` / `<source_location>` / `<memory_resource>` 全部 `file not found` | libc++15 未提供这四个 C++20/23 头（`<memory_resource>` 到 LLVM 19 才有） | 新增 `files/compat/{expected,print,source_location,memory_resource}` **同名兼容头**：构建期 `-isystem files/compat`，安装期随 `package()` 复制进 `include/`，消费者 include 即得；上游源码零改动 |
| 4 | `std::format` 在 `<format>` 里声明但不可用（`no member named 'format'`），链接缺 `typeinfo for std::format_error` | libc++15 用 `_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 关闭 format 实现；实现体在头里，`format_error` 的 typeinfo/vtable/析构在 `libc++experimental.a` | `-fexperimental-library` 打开声明面 + `-lc++experimental` 补链接面（先例：ladybug 0.18.2 `cpp_info.system_libs=["c++experimental"]`、poppler 25.12.0.2 `CMAKE_CXX_FLAGS=-fexperimental-library`）。随包用 `cpp_info.cxxflags`/`system_libs` 传给消费者 |
| 5 | `<expected>` 兼容头首版用 `std::variant<T,E>` 存储时，上游 `static_assert(omath::hashing::base64_decode("Zm9v").has_value())` 报 `non-constexpr function '~__dtor'` | libc++15 的 `std::variant` 析构不是 constexpr（`std::optional` 与 `std::string` 是，实测） | 改为 `optional<T>` + `optional<E>` 双槽存储，常量求值路径恢复 |
| 6 | aarch64 上 `OMATH_USE_AVX2` 默认为 ON，会给全部目标加 `-mfma -mavx2` 并把 `OMATH_USE_AVX2` 作为 PUBLIC 宏，使 `include/omath/linear_algebra/mat.hpp` 无条件 `#include <immintrin.h>` | `check_cxx_compiler_flag("-mavx2")` 在 aarch64 clang 上 rc=0（只报 `argument unused during compilation` 警告） | `tc.variables["OMATH_USE_AVX2"] = False` 显式关（scout 预检建议，本轮实测确认为必需） |
| 7 | `configure` 报 `Target "unit_tests" links to: GTest::gtest ... target was not found` | Conan CMakeDeps 的 gtest 目标名是 `gtest::gtest`（配方无 components），上游按 vcpkg 假设写 `GTest::*` | `patches/0001-tests-CMakeLists.txt.patch` 补包装目标（见「源码修改」节） |
| 8 | 首轮 ctest 10 例失败：`EpaComprehensive.MonotonicBuffer_MultipleReleaseCycles`（`std::bad_alloc`）+ 9 个 `*_pattern_scan_file`（`res.has_value()==false`） | ① `files/compat/memory_resource` 的 `release()` 把调用方传入的缓冲一并丢弃，第二次 `release()` 后 upstream=`null_memory_resource()` 只能 `bad_alloc`；② OHOS 拒绝 `open(/proc/self/fd/<memfd>)`（EACCES，见 0002 补丁行） | ① `release()` 按 [mem.res.pool] 只回收向上游要来的块、保留并复用构造缓冲（`m_initial_buffer`/`m_initial_capacity` 不可变副本）；② 补丁 0002 + 配方把 `TMPDIR` 指向可写构建目录。复跑 ctest **1168/1168 全绿**（框架注册 case 口径；上游分母 N=1413 见「验证结果」节） |
| 9 | `gtest` 头在 `-I` 引入时触发 `-Wcharacter-conversion`，上游默认 `OMATH_THREAT_WARNING_AS_ERROR=ON` 会把系统/依赖头警告升级成错误 | 上游 `-Wall -Wextra -Wpedantic -Werror` 与非 system 引入的依赖头叠加 | 依赖头经 CMakeDeps 的 imported target 引入（CMake 默认按 system include 处理），实测可保持上游 Werror 默认不开关；若 CI 仍红，退路是 `OMATH_THREAT_WARNING_AS_ERROR=OFF` 并在此登记 |
| 10 | CI 首轮红（build 62055）：`cmake.configure()` 报 `ConanException: Error 127`，日志成片 `Error relocating /data/service/hnp/bin/cmake: _ZTVN10__cxxabiv120__si_class_type_infoE: symbol not found`（CI 程序自报 `elapsedTime=68.224859`；失败发生在 configure 阶段，上游源码一行未编译；机器人评论时间戳为 `/rebuild` 20:13:21 → 失败评论 20:13:28，两者并存、以程序自报为准） | conan 的 VirtualBuildEnv 把 `tool_requires(clang/22.1.8)` 的 `lib/` 拼在 `LD_LIBRARY_PATH` 最前面，而该目录自带**另一份 `libc++_shared.so`**（md5 `cbae7776…`，与 SDK 的 `34f3401b…`、系统 `/system/lib64` 的 `b7a0b843…` 三者互不相同）；worker 上系统 cmake 因此先解析到它并缺符号。本机镜像相同、同款 LD_LIBRARY_PATH 下 `cmake --version` 正常，**未能本地复现**，故按「唯一环境差异 + 机制吻合」处置 | 新增 `_strip_tool_libdir_from_buildenv()`：在 `cmake.configure()` **之前**从已生成的 `conanbuildenv-*.sh` 里摘掉 tool 的 lib/（只改 `LD_LIBRARY_PATH`/`DYLD_LIBRARY_PATH` 两行；PATH 中的 clang bin/、profile 的 SDK llvm/lib（lld 依赖的 libxml2.so.16）与调用方继承值全部保留）。clang 自带 `RUNPATH=$ORIGIN/../lib`，不依赖该目录；`test_package` 同款处理（消费者进程同样跑在 conanbuild 环境里） |
| 11 | 外部审查 rule4 FAIL「少报: 上游实测 N=1413 > 声明 N=1168」（裁决件 191780157，2026-09-27 16:43，其余 12 条规则 PASS） | 原声明把 N 取成**较小候选值**（框架注册 1168），未按 §3.5「N 取候选数法最大值」取最大候选值（源码宏全 `tests/` 清点 1413）；审方取数口径同值反推：`grep -rhoE "(^\|[^A-Za-z0-9_])(TEST\|TEST_F\|TEST_P)\(" <src>/tests \| wc -l` = **1413**（与裁决「实测 N」逐字同值） | 声明 N 改为 **1413**，分栏重写为 `1413 = PASS 1162 + FAIL 0 + SKIP 0 + NOT_RUN 251`（NOT_RUN = lua 248 + modules 1 + imgui 2，均上游默认 OFF 且需额外依赖）＋已跑注册 case 1168/1168 = 100%；五处同源（`test_package/MANIFEST.yml`、版本级 `manifest.yaml`、软件级 `manifest.yaml`、`notes.md`、PR 正文）；delta T3 ⇒ 完整重验 + W4 复审；**未删除、未修改任何测试用例与断言** |

## 源码修改

**2 个补丁，均只动构建接线/测试夹具实现，不碰任何测试用例与算法逻辑**：

| 补丁 | 文件 | 原因 | 内容 |
|---|---|---|---|
| `patches/0001-tests-CMakeLists.txt.patch` | `tests/CMakeLists.txt` | Conan CMakeDeps 导出的目标名是 `gtest::gtest`（`gtest/1.17.0` 配方无 components、不导出 `gtest_main`），而上游写的是 vcpkg 风格 `GTest::*`，直接 configure 报 `target 'GTest::gtest' not found` | 在 `find_package(GTest CONFIG REQUIRED)` 之后补 `GTest::gtest`/`GTest::gtest_main` 两个包装目标；`GTest::gtest` 转发到 `gtest::gtest`，`GTest::gtest_main` 为空目标（上游 `tests/main.cpp` 自带 `main()`，gtest_main 的 main 永远不会被链接器拉入），**链接输入与用例数不变** |
| `patches/0002-tests-general-mem_fd_helper.hpp.patch` | `tests/general/mem_fd_helper.hpp` | OHOS 内核**禁止 `open(/proc/self/fd/<memfd>)`**：`memfd_create` 成功、`readlink` 正常，但 `open()` 返回 `EACCES`（raw open 探针实测），上游夹具据此交出的文件所有扫描都读不到 → 9 个 `*_pattern_scan_file` 用例 `res.has_value()==false` | memfd 路径先用 `std::fstream` 探针一次，可读则**与上游逐字节等价地返回**；被拒才回退到「唯一命名临时文件 + 析构删除」分支（`TMPDIR` 由配方指到可写构建目录）；析构/移动改为两条路径同时清理。**用例文件零改动** |

除这两个补丁外，全部工具链差异由 conanfile.py 的 CMakeToolchain 变量与 `files/compat/`
同名兼容头承载，避免补丁随上游版本漂移。

`files/compat/` 交付的四个头（每个头首部都写明用途与适用边界）：

| 头 | 补的缺口 | 覆盖的上游用法 |
|---|---|---|
| `expected` | libc++15 无 `<expected>`（C++23） | `std::expected<T,E>` 构造/观察器/比较、`std::unexpected`、`bad_expected_access` |
| `memory_resource` | libc++15 无 `<memory_resource>`（`std::pmr` 到 LLVM 19） | `memory_resource`/`monotonic_buffer_resource`/`polymorphic_allocator`/`get_default_resource`/`null_memory_resource`/`pmr::vector`/`pmr::unordered_map` |
| `source_location` | libc++15 无 `<source_location>` | `std::source_location::current()/function_name()`（基于 `__builtin_FILE/LINE/FUNCTION`） |
| `print` | libc++15 无 `<print>`（C++23，LLVM 18） | `std::print`/`std::println`（复用已打开的 `<format>`） |

## 依赖版本

- 运行依赖：**0**（上游 `vcpkg.json` 只有宿主工具 `vcpkg-cmake*`）
- 构建期 `tool_requires`: `clang/22.1.8`（编译器，ohpcd 制品仓预编译，195.7MB 包）
- 测试期 `test_requires`: `gtest/1.17.0`（`tests/CMakeLists.txt` 的 `find_package(GTest CONFIG REQUIRED)`）
- 可选依赖 `lua`/`sol2`/`safetyhook`/`imgui`/`benchmark` 全部按上游默认关闭，缺省禁用不构成止损

## 验证结果

```bash
# 采信轮（干净缓存 → conan create → 证据三份）
sh $HOME/ws/tools/conan_verify_round.sh omath 5.6.0 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
# 结果见 reports/ 与 $TASK_DIR/evidence-*.md（ctest 统计逐条登记在 reports/test-report.md）
```

- **采信轮（rule4 返修 T3 完整重验，2026-09-27）**：`conan_verify_round.sh` **RC=0**（干净轮标志
  `run_make=7 / calling_build=2 / apply_patch=2`；证据三份已落 `$TASK_DIR/evidence-acd742e/`，
  `evidence-index.json` 的 `sha`=`acd742e6457afe03f46db8bea50cb678e296b037`、`captured_at`=2026-09-27T17:20:56；
  收尾四步序：`finish … built` rc=0 → `finish_restore.sh --apply` rc=0 → `capture_evidence.py --verify` rc=1
  （3 项 finish 改写）→ 按其结论行 `--restore` rc=0 → 复跑 `--verify` **rc=0**）
- **上游单测**（统计单位 = 源码宏 `TEST|TEST_F|TEST_P`，命令 `ctest --test-dir tests --output-on-failure --no-tests=error` 实跑）：
  **N = TOTAL 1413 = PASS 1162 + FAIL 0 + SKIP 0 + NOT_RUN 251**，通过率 1162/1413（82.24%）；
  其中框架注册的 **1168 个 gtest case 全部 PASS（1168/1168 = 100%）**，采信轮日志原文
  `100% tests passed, 0 tests failed out of 1168`
- **N 的取数（§3.5 候选数法最大值）**：源码宏全 `tests/` 清点 **1413**（general 855 + engines 309 +
  lua 248 + modules 1）为最大候选值，故 N=1413；框架注册数 1168 为次大候选值（并列记录、不作 N）。
  差额逐项归因：`1413 − 248（tests/lua，上游 OMATH_ENABLE_LUA 默认 OFF） − 1（tests/modules，OMATH_ENABLE_MODULES 默认 OFF）
  − 2（imgui 集成整文件 #ifdef，上游默认 OFF） = 1162` 源码宏实跑；`1162 + 6（TEST_P 1 宏展开 7 个参数化实例）= 1168` 注册 case。
  四项口径与命令见 `test_package/MANIFEST.yml` 的 `test_counting`。
  **返修记录**：外部审查 191780157（2026-09-27）rule4 判「少报: 实测 N=1413 > 声明 N=1168」，
  根因是原声明取了较小候选值（框架注册 1168）而非最大候选值——本轮已按候选数法改声明为 1413，
  NOT_RUN 251 逐项归因，**未删除或修改任何测试用例与断言**。
- **消费者 test_package**：6/6 PASS，日志原文 `omath consumer checks passed: angle=10deg between=90deg base64=foo`
- **逐字证据**：`reports/test-report.md`（两表四口径 + 修复前后对照）、`reports/conan-create.log`（干净轮权威副本）

## 注意事项

1. **下游消费者同样需要 clang≥18**：omath 的数学头是模板（浮点 NTTP），任何实例化
   `omath::Angle` 的下游 TU 都必须同样 `tool_requires("clang/22.1.8")` 并沿用本配方的
   libc++/sysroot include、lib 路径。仅使用打包好的非模板编译单元（pattern scan、hashing）
   的消费者不受此限制。
2. **`-fexperimental-library` 与 `libc++experimental` 必须成对**：只开编译旗标不链库会报
   `undefined symbol: typeinfo for std::format_error`（已由 `cpp_info.cxxflags` +
   `cpp_info.system_libs` 随包传递）。
3. 上游 `pixi/`、`vcpkg.json`、`xmake.lua` 是其他包管理器的入口，本仓不使用；
   `pixi/run.unit.tests.cmake` 等价于本包的 `ctest --test-dir tests`。
4. 设备 `os.cpu_count()=20` 而 affinity=8，配方显式 `tools.build:jobs=4` 防超订。
