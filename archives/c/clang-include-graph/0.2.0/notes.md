# clang-include-graph 0.2.0 (HarmonyOS PC adaptation notes)

## What it is

`clang-include-graph` is a libclang-based CLI that analyses a C++ project's
include graph (topological sort / tree / dependants / graphviz / graphml /
plantuml / json). Upstream: github.com/bkryza (Apache-2.0). It is an
**application** package: upstream installs a single binary and nothing else.

## Why this shape

- Requires **compiled** Boost.Log (log + log_setup), Boost.JSON and
  Boost.Test (unit_test_framework) plus filesystem/graph/program_options.
  No published ohpcd boost carries compiled log/json/test, so the
  `boost/1.91.0.1.3` variant (sibling branch) was built first.
- Requires **libclang**. There is no ohpcd clang recipe and conancenter is
  disabled, but the on-device OHOS SDK toolchain (`native/llvm`, clang 15.0.4)
  ships a usable arm64 `libclang.so` (NEEDED only libc.so), `clang-c/Index.h`
  and a working `llvm-config`. An earlier assumption that the device had no
  libclang was wrong (the `.harmonybrew/ndk` symlink did not resolve).

## Key findings

1. **Runtime probe (not inference):** a code-signed aarch64 executable linked
   against the SDK `libclang.so` loads it and parses a translation unit via
   the C API on the device. `DT_NEEDED` is only `libclang.so` + `libc.so`.
   → Path A is structurally viable.
2. Upstream `CMakeLists.txt` declares `LLVM_PREFERRED_VERSION 16.0.0`, but
   `FindLibClang.cmake` never enforces a minimum — it only resolves through
   whatever `llvm-config` it finds. Pointing `LLVM_CONFIG_PATH` at the SDK
   `llvm-config` (15.0.4) is accepted.
3. `libclang.so` is not a conan dependency, so no `VirtualRunEnv` covers it.
   The SDK lib dir must be baked into the executable RPATH
   (`-Wl,-rpath,<native/llvm>/lib`) or the loader cannot resolve `libclang.so`.
   The probe for that root must require `lib/libclang.so`, not just a
   `bin/llvm-config` shim: the `.harmonybrew` Cellar exposes a pseudo-root
   (`…/26.0.0.18_1`) whose `bin/llvm-config` realpaths through it but which has
   no `lib/`, so a `bin/llvm-config`-only probe baked a nonexistent
   `-Wl,-rpath,…/26.0.0.18_1/lib` and every CTest executable died at load with
   `Error relocating … clang_createIndex: symbol not found`.
4. OHOS loads only code-signed ELF → binaries are signed with
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool ... -selfSign 1`
   before the upstream CTest gate and again in `package()`.
5. `lib-clang-include-graph` is an **OBJECT library** (all `src/*.cc` except
   main.cc) that only the executables link against. Its Boost.JSON/Log/asio
   sources therefore need the boost headers via a global flag
   (`-isystem <boost include>`); the upstream `include_directories(${Boost_INCLUDE_DIRS})`
   legacy variable is not guaranteed by the conan `BoostConfig`.
6. `GitVersion.cmake` yields `0.0.0-unknown` outside a git checkout →
   configure pins `GIT_VERSION=0.2.0`.
7. The parser runs Boost.Log through a global severity logger and a Boost.Asio
   thread pool, so `boost/asio/thread_pool.hpp` and `boost/asio/post.hpp` must
   resolve on the include path. They are header-only, but the boost/1.91.0.1.3
   build closure excludes the whole asio/context family (the CMake superproject
   text scanner would pull Boost.Context, which has no aarch64 asm for OHOS),
   so the CMake install does NOT stage them — the first real verify failed at
   include_graph_parser.h:25 (`thread_pool.hpp: file not found`). The boost
   variant was amended to copy the asio header tree (`boost/asio.hpp` +
   `boost/asio/`) in `package()`; its core is an INTERFACE over headers the
   closure already installs (align/assert/config/system/throw_exception). The
   log emits to no sink unless configured — stdout carries only the graph.

## Validation gate (inside `conan create`, build())

- Upstream CTest suite: nine tests (topological_sort/cycles/tree/dependants/
  graphviz/graphml/plantuml/json/.. printers + util), each linking libclang
  and the Boost targets — runs after signing, under the conan run env.
- `test_package` runs the packaged binary against a self-contained fixture
  TU (`compile_commands.json` driving a real libclang parse) and asserts the
  include graph contains the expected header edges; plus a `--version` smoke.

## Not modified upstream

No patches (`patches: []`): the adaptation is entirely in recipe wiring
(device SDK discovery, RPATH, `-isystem`, signing, test fixtures).

## Review-gate fix (2026-09-08, MR #8889)

Reviewer bengbeng2345 flagged rule4 少报 (declared upstream N < measured).
Fix is declaration-only (no source/build change):

- MANIFEST `upstream_tests` now enumerates every actually-executed upstream
  test executable = **9** (test_topological_sort / test_cycles / test_tree /
  test_dependants / test_graphviz / test_graphml / test_plantuml printers,
  test_util, test_json_printer), one entry per `tests/*.cc`, all run by the
  single tests/ CTest suite inside build() (device evidence 9/9 PASS).
  Declared upstream 合计 9 ≥ reviewer-measured 8; 用例数 = 测试程序/目标数.
- Note: the CI L0i failure on this PR was the boost/1.91.0.1.3 dependency not
  yet on the ohpcd registry (registry_unreachable) — that clears when MR #8870
  merges and boost/1.91.0.1.3 is released; then a `/rebuild` re-runs CI.
