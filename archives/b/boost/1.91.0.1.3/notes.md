# Boost 1.91.0.1.3 clang-include-graph dependency notes

## Scope

clang-include-graph 0.2.0 unconditionally links `Boost::log`
(`-DBOOST_LOG_DYN_LINK`) and its CMake resolves
`find_package(Boost COMPONENTS graph program_options filesystem log_setup log
unit_test_framework json)`. No Boost package published on the farm remote
(ohpcd) ships the **compiled** Boost.Log libraries (checked 1.84.0 → 1.90.0.4.1
→ 1.91.0.1.1), so this suffix variant adds them.

Base = the verified `boost/1.91.0.1.1` Redex recipe + `boost-1.91.0-1-cmake`
source asset (identical `conandata.yml`/patch). The OHOS portability fixes in
the base recipe already prove that the Boost.Log dependency closure
(thread/chrono/date_time/container/atomic/system/filesystem) compiles on the
device clang-15 / libc++-15 toolchain.

## What this version adds over boost/1.91.0.1.1

- `BOOST_INCLUDE_LIBRARIES`: `json;log;test` added (keeps the whole Redex set).
- Compiled components published: `Boost::log` (`libboost_log.so`),
  `Boost::log_setup` (`libboost_log_setup.so`),
  `Boost::unit_test_framework` (`libboost_unit_test_framework.so`),
  and `Boost::json` (`libboost_json.so`).
- Boost.JSON is NOT header-only in the 1.91 CMake superproject: it compiles
  `libboost_json` from `src/src.cpp`, and its headers carry no
  `BOOST_JSON_HEADER_ONLY` toggle. Publishing it as header-only left consumers
  of `boost::json::parse`/`value`/`object` with undefined symbols.
- `Boost::log` carries its compiled closure as cpp_info requires (atomic,
  chrono, container, date_time, filesystem, system, thread, headers);
  `Boost::log_setup` requires `Boost::log`.
- Ships the header-only Boost.Asio core (`boost/asio.hpp` + `boost/asio/`):
  clang-include-graph includes `boost/asio/post.hpp` and
  `boost/asio/thread_pool.hpp`, but asio is excluded from the build closure
  (the superproject text scanner would drag Boost.Context in, which has no
  OHOS aarch64 asm), so the CMake install would otherwise never stage those
  headers. Boost.Asio core is an INTERFACE over align/assert/config/system/
  throw_exception (already installed), so `package()` copies the asio header
  tree from the source tarball — no compiled `libboost_*` is added.

## Validation plan

1. `conan create` on device (`ohos-aarch64` profile, WIN01 home): builds the
   shared set and runs the retained upstream suites (ProgramOptions/iostreams/
   regex/Boost.Graph leaf — the same 18 flows as 1.91.0.1.1).
2. Boost.Log upstream suite (`libs/log/test`) is intentionally outside the
   build-tree gate; its runtime behaviour is proven by the new test_package
   consumer `boost_log_contract` (real text-file sink round trip with
   `add_file_log`, plus Program_options/JSON/Filesystem usage mirroring
   clang-include-graph's own link set).
3. After PASS this package unblocks `feat/clang-include-graph-0.2.0`.

## Version contract

- New suffix 1.91.0.1.3 (distinct from the *upstream* mailio-oriented
  1.91.0.1.2 branch and from ohpcd boost/1.91.0.1.1). No published boost
  revision is modified.

## Review-gate fix (2026-09-08, MR #8870)

Reviewer bengbeng2345 flagged rule4 少报 (declared upstream N < measured) and a
stale AI 代码审查 comment. Fix is declaration-only (no source/build change):

- MANIFEST `upstream_tests` now enumerates every actually-executed upstream
  target = **18** (14 ProgramOptions unit programs, then integration leaves
  multiprecision `reduced_cpp_double_fp` / iostreams `test_fd` / regex `quick` /
  graph `disjoint_set`), the same 18 flows already documented above and matched
  by the device ctest evidence (upstream-components 15/15, upstream-iostreams
  1/1, upstream-regex 1/1, test_package `boost_graph_upstream_disjoint_set`).
  Declared upstream 合计 18 ≥ reviewer-measured 14; 用例数 = 测试程序/目标数.
- Pushing the fix refreshes the atomgit-bot 代码审查 comment in place (rule6).
