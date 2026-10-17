# neovim 0.11.3 headless dependency package

## Purpose

This package is the first dependency package for the `nvim-lspconfig/2.5.0`
Path B candidate:

```text
packaged nvim --headless + packaged vusted -> nvim-lspconfig make test
```

The immediate goal is not a full interactive Neovim migration.  It is to prove
that the `nvim` binary can be built, signed, installed, and run in headless mode
on OHOS.

## First package route

The first recipe intentionally uses Neovim's bundled dependency build
(`USE_BUNDLED=1`) instead of splitting every dependency into Conan packages.
This keeps the initial failure surface focused on Neovim's native build and
runtime behavior.

If this succeeds, the follow-up Path B route should replace bundled downloads
with dependency PRs where needed, then add:

- `lua-say >= 1.4-1`
- `lua_cliargs/3.0`
- `luasystem >= 0.4.5`
- `dkjson >= 2.1.0`
- `mediator_lua >= 1.1.1`
- `busted/2.2.0`
- `vusted/2.5.3`

## Smoke target

The package is considered useful only if the OHOS run can execute:

```bash
nvim --version
nvim --headless -u NONE -i NONE '+lua print(vim.version().major)' +qa
```

The final `nvim-lspconfig` Path B evidence still requires:

```bash
make test
# upstream command: vusted ./test
```

## Current status

- `2026-08-04 19:06 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-190627-43330`
  failed before build because the fresh isolated `CONAN_HOME` generated a
  default `settings.yml` without the `OHOS` enum. For isolated jobs on the
  current device, copy `$HOME/.conan2/settings.yml` into the job `CONAN_HOME`
  after running `ci/conan/setup.sh`.
- `2026-08-04 19:13 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-191311-45005`
  reached `build()` and failed because this device profile exposes native OHOS
  clang/cmake via `tools.build:compiler_executables`, but does not provide an
  SDK `ohos.toolchain.cmake`. The recipe now falls back to those profile
  compilers with `CMAKE_SYSTEM_NAME=Linux` and `CMAKE_SYSTEM_PROCESSOR=aarch64`
  when no toolchain file is present.
- `2026-08-04 19:19 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-191920-47370`
  built into bundled LuaJIT and failed at `ar rcus libluajit.a` with exit 127
  because the device has `llvm-ar`/`llvm-ranlib`/`llvm-strip`, but no bare
  `ar`. The recipe now passes `CMAKE_AR`, `CMAKE_RANLIB`, and `CMAKE_STRIP`,
  and patches Neovim's bundled `BuildLuajit.cmake` to invoke LuaJIT make with
  `"TARGET_AR=${CMAKE_AR} rcus"` and `"TARGET_STRIP=${CMAKE_STRIP}"`.
- `2026-08-04 19:26 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-192605-51902`
  proved the LuaJIT archive fix works (`Completed 'luajit'`), then stalled in
  parallel CMake/Ninja bundled dependency downloads after GitHub HTTP/2 receive
  failures for `lua_compat53` and `treesitter_markdown`. The stale holder lock
  for this run was removed after confirming no matching process remained. The
  recipe now rewrites bundled GitHub URLs in `cmake.deps/deps.txt` through
  `gh-proxy.com` and exports `CMAKE_BUILD_PARALLEL_LEVEL=1` for both `deps` and
  `nvim` builds.
- `2026-08-04 19:34 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-193430-57344`
  confirmed bundled GitHub downloads now use `gh-proxy.com`, then failed in
  bundled `libuv/1.50.0` at `src/unix/core.c` because OHOS musl does not expose
  Linux CPU affinity APIs (`CPU_SETSIZE`, `cpu_set_t`, `sched_getaffinity`,
  `CPU_COUNT`). The recipe now injects a bundled libuv patch command that
  disables `UV__CPU_AFFINITY_SUPPORTED` and the `uv_available_parallelism()`
  Linux affinity branch on `__OHOS__`, matching the existing standalone
  `libuv/1.52.1` adaptation direction.
- `2026-08-04 19:43 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-194326-62083`
  was queued behind another user's
  `codex-gccsnap-gcc-snapshot-gcc-snapshot-20260705-20260804-conan-20260804-193923-59576`
  heavy run and never entered L0/build. The waiting process was stopped after
  confirming the external lock holder was still alive. The bundled libuv patch
  remains unverified and should be the next run target once the global lock is
  free.
- `2026-08-04 20:54 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-205444-53221`
  waited behind `gcc12`, then started immediately when the lock changed. It
  verified the bundled libuv CPU-affinity guard: `core.c` compiled past the
  previous `CPU_SETSIZE`/`cpu_set_t` failure. The next failure was bundled
  libuv `src/unix/udp.c`, where OHOS lacks Linux `struct mmsghdr`,
  `recvmmsg`, and `sendmmsg`. The recipe now extends `PatchLibuvOhos.cmake` to
  exclude `__OHOS__` from the libuv mmsg branches, matching the existing
  standalone `libuv/1.52.1` `udp.c` adaptation.
- `2026-08-04 21:36 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-213607-34574`
  verified the bundled libuv mmsg guard: dependencies completed and bundled
  parser shared objects were signed. The main Neovim CMake configure then
  failed at `find_package(Iconv REQUIRED)` because `ICONV_INCLUDE_DIR` was not
  found. Neovim's bundled `FindIconv.cmake` only requires `iconv.h`, so the
  next spike enables `USE_BUNDLED_LIBICONV=ON` in the dependencies phase and
  checks whether `.deps/usr/include` feeds the main configure.
- `2026-08-04 21:59 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-215957-18694`
  entered immediately after the prior `gcc12` lock released, but enabling
  Neovim's bundled libiconv failed earlier in `BuildLibiconv.cmake`: upstream
  only supports that bundled path for MSVC and rejects `Linux/Clang`. The spike
  therefore uses the existing `libiconv/1.17` Conan package, passes
  `ICONV_INCLUDE_DIR` and `ICONV_LIBRARY` to Neovim's main configure, and
  extends `FindIconv.cmake` to also link `CHARSET_LIBRARY` when the static GNU
  libiconv package exposes it.
- `2026-08-04 22:26 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-222647-36891`
  proved the packaged libiconv route: main CMake found Iconv and generated the
  Neovim build. The build then failed at final `bin/nvim` link because bundled
  libuv was configured as `HarmonyOS` and did not include its Linux source
  group (`src/unix/linux.c`, `procfs-exepath.c`, `random-getrandom.c`,
  `random-sysctl-linux.c`, and related proctitle handling). The recipe now
  patches bundled libuv `CMakeLists.txt` so `HarmonyOS` uses the Linux source
  group while retaining the OHOS guards for unsupported CPU affinity and mmsg
  APIs.
- `2026-08-05 00:15 +0800`, run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.11.3-neovim-0.11.3-headless-spike-conan-20260804-224549-7979`
  passed. The bundled libuv `HarmonyOS` source-group patch fixed the previous
  final-link missing-symbol failure; `bin/nvim` linked, was signed, and ran:
  `nvim --version` printed `NVIM v0.11.3`, and
  `nvim --headless -u NONE -i NONE '+lua print(vim.version().major)' +qa`
  printed `0`. `cmake --install` packaged the binary, runtime, and parser
  modules, the package ELF files were signed, `test_package/test_headless.sh`
  repeated both smoke commands successfully, and CI ended with
  `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=pass`, `L4_RESULT=pass`,
  `L5_RESULT=pass`, `Total: 1`, `Success: 1`, `Failed: 0`.
- `2026-08-07 04:02 +0800`, Path B integration job
  `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806`
  rebuilt this package in the same isolated Conan home later used by
  `vusted/2.5.3-1` and `nvim-lspconfig/2.5.0`. Run directory:
  `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-neovim-vusted-pathb-build-neovim-r1-20260807-040203-8515`.
  Full package reference:
  `neovim/0.11.3#57ae57a19bbb8bd8cd1497c771deb676:197d0cbd425ab3ff9646103c201907cc253279b2#f67affc2fcab2f632fd282bdfaf7e87b`.
  The test package printed `NVIM v0.11.3` and `0` from
  `nvim --headless -u NONE -i NONE '+lua print(vim.version().major)' +qa`.
  CI result remained `L0/L1/L2/L4/L5` pass with `Total: 1`, `Success: 1`,
  `Failed: 0`.
- `2026-08-07 22:07 +0800`, CI-fix validation run
  `/storage/Users/currentUser/ohos-test-runs/codex-a-neovim-neovim-ci-fix-nlua0-r2-20260807-20260807-220732-19095`
  verified the MR CI failure for `build/lib/libnlua0.so` linking against
  bundled LuaJIT. The recipe now patches Neovim's main CMake so `nlua0` links
  `${LUAJIT_LIBRARY}` when `CMAKE_SYSTEM_NAME` is `OHOS` or `HarmonyOS`, in
  addition to upstream's Windows-only branch. Full package reference:
  `neovim/0.11.3#44518ef04529836b17c2040f91b59d7d:197d0cbd425ab3ff9646103c201907cc253279b2#69719dde8b6d2a7c02e1a420c6fa6c2d`.
  The run passed the previous `nlua0` link point, signed `bin/nvim`, and
  `test_package` printed `NVIM v0.11.3` plus `0` from the headless Lua smoke.
  CI result: `L0/L1/L2/L4/L5` pass, `Total: 1`, `Success: 1`, `Failed: 0`.
