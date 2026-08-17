# Boost 1.90.0.1 Morpheus dependency notes

## Scope

This package is the Morpheus-specific repair suffix for upstream Boost 1.90.0.
The existing `boost/1.90.0` recipe is header-only, while Morpheus CLI needs
linkable Boost components:

- `Boost::program_options`
- `Boost::filesystem`
- `Boost::system`

The recipe therefore uses the official Boost CMake release asset and builds
only the minimal dependency closure: `atomic`, `container`, `filesystem`,
`program_options`, and `system`. It intentionally does not copy the larger Redex/FastNetMon
component set from other open PRs.

## Issue/PR split

- Morpheus task: Issue #1298
- Dependency issue: #1480
- Branch: `feat/boost-1.90.0.1-morpheus`
- File scope: `archives/b/boost/1.90.0.1/**`

The issue text explicitly states that this is the Morpheus-required version and
that existing `boost/1.90.0` header-only artifacts are a different version
contract.

## Validation plan

1. Rerun Windows/MinGW Conan simulation for `boost/1.90.0.1` once the source
   archive can be fetched reliably.
2. Run OHOS single-package validation for `boost/1.90.0.1`.
3. After publication, run Morpheus with this package in the host dependency
   graph.

The consumer test verifies that CMake can resolve and link
`Boost::program_options`, `Boost::filesystem`, and `Boost::system`.

## Local status

Static checks passed on 2026-07-26:

- `python -m py_compile conanfile.py test_package/conanfile.py`
- `conan inspect`
- `conan export`
- `git diff --check`

Windows/MinGW `conan create` was started with workspace-local `CONAN_HOME` and
`TEMP/TMP`, but did not reach configure/build. The GitHub
`boost-1.90.0-cmake.tar.xz` source archive is 101.6MB; the local run timed out
after 20 minutes at 31,129,600 bytes downloaded. Next execution should either
reuse a completed source cache or run on the OHOS worker/network path.

## OHOS status

2026-07-28 r7 on the isolated OHOS job built and installed the four shared
libraries `libboost_atomic.so`, `libboost_container.so`,
`libboost_filesystem.so`, and `libboost_program_options.so`, then signed them
successfully. The generated consumer executable was also built and signed.

The complete OHOS wrapper run passed:

- run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-boost-boost-1.90.0.1-20260728-r1-conan-r7-l5nopipe-20260728-150149-22007`
- package revision: `boost/1.90.0.1#0e67c4d18533fbb41099c63f30d3c12f:01d92cf349a0dd98ff915f4bd99a04430171517f#2b240dcba2008dc970dc4599973c4e74`
- L0=pass, L1=pass, L2=skip(no bin/ dir), L4=pass, L5=pass
- Build Summary: Total 1, Success 1, Failed 0

Earlier r5/r6 wrapper runs exited 141 after `conan create` had already printed
`[ok] boost/1.90.0.1 -- conan create passed`. The cause was in CI L5/R26
post-processing, where `find | head` and `ls | xargs` pipelines can trip zsh
`pipefail`/SIGPIPE while scanning large package/system library trees. The CI
wrapper now uses `find -print -quit` and direct zsh glob iteration instead of
those pipelines.

Manual reruns of the same signed `test_boost_morpheus_components` executable
returned 0 both with and without `conanrun`; an independent OHOS runner
`conan test` also regenerated, built, signed, and executed the test package with
exit code 0. Dynamic inspection confirmed
`libboost_program_options.so` has `NEEDED libboost_container.so`, so the Conan
component metadata now exposes `Boost::container` and makes
`Boost::program_options` require it.

## Upstream component tests

The full Boost test suite is large and Boost.Build based, so this PR validates
the Morpheus-relevant official component quick tests from the release source:

- `libs/system/test/quick.cpp`
- `libs/filesystem/test/quick.cpp`
- `libs/program_options/test/quick.cpp`

These three official tests were cross-compiled against the r7 Conan package,
signed, and executed on the OHOS device. Run directory:
`/storage/Users/currentUser/ohos-test-runs/codex-a-boost-boost-1.90.0.1-20260728-r1-upstream-quick-r1-20260728-150919-25874`.
Result: 3/3 passed (100.00%).

---

# Boost 1.90.0.4.1 — pinocchio 4.1.0 unit_test_framework 组件（新增 test 模块）

## 背景

pinocchio 4.1.0 上游 `unittest/CMakeLists.txt` 使用：

```cmake
find_package(Boost COMPONENTS unit_test_framework)
# 每个测试目标:
target_compile_definitions(<test> PRIVATE BOOST_TEST_DYN_LINK BOOST_TEST_MODULE=...)
modernize_target_link_libraries(<test> SCOPE PRIVATE TARGETS Boost::unit_test_framework ...)
```

因此 boost 包必须提供 `Boost::unit_test_framework`（链接 libboost_unit_test_framework.so）以及
`include/boost/test/` 头文件。1.90.0.3 及之前所有已发布版本都不含 test 组件。

## 本次改动（在 1.90.0.3 基础上只增不减）

1. **conanfile.py `BOOST_INCLUDE_LIBRARIES` 新增 `test` 组件**，并显式补 `describe;exception`
   （libs/test 的 `_boost_test_dependencies` 里除 describe/exception 外均已在此前版本列出）。
   - `libs/test/CMakeLists.txt` 用 `boost_test_add_library` 生成三个目标：
     `boost_unit_test_framework`（shared）、`boost_prg_exec_monitor`（shared）、
     `boost_test_exec_monitor`（STATIC，始终静态）。
   - BoostRoot.cmake 的 `__boost_gather_dependencies` 会自动把 test 依赖的 header-only 库
     （algorithm/assert/bind/config/core/detail/describe/exception/function/io/iterator/mpl/
     numeric_conversion/optional/preprocessor/smart_ptr/static_assert/type_traits/utility）
     捎带进来并安装，无需全部显式列出。
   - `_boost_test_dependencies` 全是 header-only（INTERFACE）库，因此
     `libboost_unit_test_framework.so` 仅 NEEDED `libc++_shared.so`/`libc.so`，
     无编译型 boost 依赖，构建成本仅 ~21 个 src/*.cpp。

2. **package_info() 新增 `unit_test_framework` 组件**：
   - `_component_library("unit_test_framework")` 精确命中 `boost_unit_test_framework`（collect_libs）。
   - `cmake_target_name = "Boost::unit_test_framework"`（与上游 boost-cmake 目标名一致）。
   - `requires = ["headers"]`（无编译型依赖）。
   - `defines = ["BOOST_TEST_DYN_LINK"]`（仅 shared 时）——对齐上游 boost-cmake 对共享版
     unit_test_framework 目标 PUBLIC 传播 BOOST_TEST_DYN_LINK 的行为；pinocchio 自己也定义
     同值宏，无冲突。

3. **test_package 新增最小消费者** `test_unit_test_framework.cpp`：
   `#define BOOST_TEST_MODULE` + `#include <boost/test/unit_test.hpp>` +
   `BOOST_AUTO_TEST_CASE`，CMake 里 `find_package(Boost ... COMPONENTS ... unit_test_framework)`
   并链接 `Boost::unit_test_framework`、PRIVATE 定义 `BOOST_TEST_DYN_LINK`
   （与 pinocchio 的 target_compile_definitions 写法一致）。conanfile.py 现在对两个测试可执行
   文件都做 OHOS 签名并运行。

## conandata.yml

零新补丁。test 模块是同一 CMake 构建内的另一个模块，已有的
`0001-cmake-avoid-versioned-soname-links-on-ohos.patch`（配合
`BOOST_INSTALL_NO_VERSIONED_LIBS=TRUE`）对 test 库同样生效——
包内无 `libboost_unit_test_framework.so.1.90.0` 版本化软链。

## 验证结果（W3，2026-08-11）

- `ohc-run.py conan-verify boost 1.90.0.4.1` 全部门禁通过（G0-G4 + L2/L4/L5），
  日志 `archives/b/boost/1.90.0.4.1/reports/conan-create.log`。
- 包内产物：`include/boost/test/unit_test.hpp`（完整 boost/test 树）、
  `lib/libboost_unit_test_framework.so`（已签名，含 .codesign）、
  `lib/libboost_prg_exec_monitor.so`、`lib/libboost_test_exec_monitor.a`。
- 最小消费者 `test_boost_unit_test_framework` 编译/链接/签名/运行：
  `Running 1 test case... *** No errors detected`。
