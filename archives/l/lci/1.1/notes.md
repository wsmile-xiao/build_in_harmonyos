# lci 1.1 OHOS PC adaptation notes

Date: 2026-09-07. Environment: HarmonyOS PC (HongMeng 1.12.0, aarch64),
self-hosted toolchain (clang 15.0.4, CMake 4.1.2, make 4.4.1), conan 2
with the repo's `ci/conan/profiles/ohos-aarch64` profile.

## Upstream identity

- Upstream: https://github.com/chatziko/lci (Yannis Chatzikoannides), pure
  lambda calculus interpreter, GPL-2.0-only. Not to be confused with
  justinmeza/lci (a LOLCODE interpreter, no 1.1 release).
- Version: v1.1 tag, released 2024-12-14; archive
  `lci-v1.1.tar.gz` SHA256
  `51725e33a7066100757b7da84b2290a651a5f47b985eb3e3647acd871964cd58`.
- The release archive embeds the sources but not the two git submodules.
  The v1.1 tree pins dparser@a810bbcd0aab0825b447883bfc8294a2c94c3df6 and
  replxx@d13d26504f97ed2a54bc02dd37d20ef3b0179518; both were fetched as
  GitHub archive tarballs and verified byte-identical to a recursive
  submodule checkout of the tag.

## Build

CMake >= 3.3. Single `lci` executable; `dparser` (C) provides the
`make_dparser` generator that runs at build time to emit
`grammar.g.d_parser.c`; `replxx` (C++) provides REPL line editing and links
`stdc++`.

Trial configuration/build on the OHOS PC itself:

- `cmake_minimum_required(VERSION 3.0)` inside dparser is rejected by
  CMake 4.1.2. Fixed with `CMAKE_POLICY_VERSION_MINIMUM=3.5` cache
  variable (E187); bumping the submodule's CMakeLists would also work
  (E103) but the cache flag avoids patching a third-party subproject.
- `make_dparser` executes natively on the self-hosted environment (no
  cross gap, no E359 mapping); it ran without an explicit signing step —
  but the packaged binary is still signed per repo policy (E486/E489).

## musl portability (patch 0001)

`src/run.c` selects terminal ioctls per platform. Linux/glibc takes the
`<termio.h>` branch; on musl `__has_include(<termio.h>)` is false, so the
termios branch compiles, and its unconditional

```c
#define TCGETA TIOCGETA
#define TCSETA TIOCSETA
```

breaks: musl's `bits/ioctl.h` already defines `TCGETA=0x5405` /
`TCSETA=0x5406` and defines neither `TIOCGETA` nor `TIOCSETA`. Result:
`error: use of undeclared identifier 'TIOCSETA'` (first real root cause of
the failed build). Patch guards both defines with `#ifndef`, leaving
glibc/macOS behavior unchanged. This is a genuine cross-project musl
portability pattern (any code with the same System V fallback dance);
recorded as two knowledge drafts: DRAFT-E565 (the concrete macro
redefinition compile-error mechanism) and DRAFT-E567 (the methodology
upgrade: compile-time capability guards for all legacy System V termio
ioctl macros — never fake macros, hardcode ioctl numbers, or skip
terminal functionality; keep the POSIX termios path).

The patch body is a zero-context (-U0) hunk on purpose: the guarded
region sits among tab-indented and blank context lines, and a standard
context diff would embed `" \t"` / trailing-space lines in the patch
file itself (tripping `git diff --check`, which flags those in staged
new files). Verified applicable by both patch engines that matter here:
Conan 2.29.1's patch_ng (what `conan create` actually uses, strip=0,
byte-identical result) and `git apply --unidiff-zero -p1` (byte-identical
result). GNU `patch(1)` historically off-by-ones zero-context hunks, so
use one of the two verified engines when applying by hand.

## Runtime behavior verified

- Installed layout: `bin/lci`, `share/lci/.lcirc`, `share/lci/queens.lci`.
- `DATADIR="${CMAKE_INSTALL_PREFIX}/share"` is compiled in, so the packaged
  interpreter loads its prelude from the package folder regardless of cwd.
- `Consult 'queens.lci'` resolves relative to the cwd (upstream CTest runs
  from the build directory for this reason); test_package stages its own
  copy and runs there.
- Non-tty stdin skips the raw-mode path entirely (piped tests), but the
  tty path is real and is now exercised: `ohos_specific_test.py` runs the
  packaged `bin/lci` in an actual pseudo terminal (`pty.fork`,
  `TERM=xterm`), which drives the replxx/termios raw-mode init code the
  patch guards — banner, `lci> ` prompt, `Head [7, 8, 9]` => `7`
  (27 reductions), clean EOT exit 0, all asserted.
- Church numeral 1 prints as the alias `I` (from `.lcirc`'s `I = 1` alias),
  so the queens solution list reads `[[I, 3, 5, 2, 4], ...]`.

## Tests

Tests are counted by independent test entries:

- Upstream (run inside `conan create`, via `cmake.test()`): the upstream
  CMakeLists.txt defines 4 CTest cases — `build`, `queens`, `fixed_point`,
  `valgrind`. The first three are unconditional: they were registered and
  executed on OHOS aarch64 and all passed (3/3 registered tests). The 4th
  (`valgrind`) is gated by `find_program(VALGRIND valgrind)` +
  `if(VALGRIND)`: the current OHOS target environment has no valgrind
  binary, and this repo's archives have no valgrind Conan package, so
  upstream CMake itself does not register it — it is neither failed, nor
  passed, nor removed (same behavior as upstream CI on hosts without
  valgrind). Final CTestTestfile.cmake registers 3 tests, all executed and
  passed.
- Consumer (`test_lci.sh`, 1 entry, internally 3 scenarios / 7 assertions):
  upstream queens expression (exact 10-solution list), upstream fixed_point
  expression (cycle-removal message + exact `[3, 4, [], 5]` result), and
  prelude arithmetic (`Mult 3 4`→12, `Exp 2 10`→1024, `Monus 20 8`→12,
  `Length`→5). All output formats were captured from the real interpreter
  before writing assertions.
- OHOS-specific (`ohos_specific_test.py`, 1 entry, internally 6
  checkpoints, fail closed — any check error is a failure, no silent
  skips): ohos-elf-identity (direct ELF header parse: ELF64
  little-endian, e_machine == EM_AARCH64), ohos-musl-interpreter
  (PT_INTERP parsed from program headers, exactly
  `/lib/ld-musl-aarch64.so.1`), ohos-codesign (`.codesign` section from
  the E486/E489 signing step), ohos-no-rpath (no RPATH/RUNPATH dynamic
  entries), ohos-no-build-paths (no build-machine absolute paths embedded
  in the binary), ohos-pty-repl (real pty REPL session as described
  above — the checkpoint that actually executes the patched code path;
  deterministic expression `Head [7, 8, 9]` => `7` and EOT exit 0 both
  strictly asserted). Supersedes the earlier `test_lci_ohos.sh` entry
  (one execution, one count — the shell suite is removed to avoid
  double-counting the same checks).

## 最终状态

**编译结束**: 2026-09-08
**最终状态**: built — recipe/patch/test_package 全链路绿（上游定义 4 项
CTest 测试，OHOS 环境注册并执行 3 项、3/3 通过，条件性 valgrind 测试因目标
环境无 valgrind 未注册；consumer 1/1 条目（3 场景 7 断言）；ohos-specific
1/1 条目（6 检查点））。

## 2026-09-09 整改

- 新增知识草稿 DRAFT-E567（termio ioctl 宏能力守卫方法论），编号经全域
  冲突检查（graph 540-542 / drafts 543-556+565 / 其他 worktree 557-561+
  563-564+566 / git 历史 562+573 → 567 为首个完全可用编号）。
- `test_package/ohos_specific_test.py` 新增为独立鸿蒙特有套件（6 检查点），
  取代 `test_lci_ohos.sh`（避免同一次执行重复计数）。
- 测试统计口径修正：经复核上游 CMakeLists.txt 共定义 4 个 add_test
  （build、queens、fixed_point、valgrind），此前"上游 CTest 3/3"表述
  少报了定义总数。统一口径为：上游定义 4 项；OHOS 构建注册并执行 3 项，
  3/3 通过；条件性 valgrind 测试由 `find_program(VALGRIND valgrind)` +
  `if(VALGRIND)` 控制，当前 OHOS 目标环境无 valgrind、仓库 archives/ 内
  亦无 valgrind Conan 配方，故上游 CMake 自身未注册该项——既非失败、
  非通过、也非删除。不修改上游测试代码，不伪造 4/4。

## 2026-09-10 整改（本轮审查四项）

- conandata.yml（R39）：删除 sources/dparser/replxx 三处手写的
  gh-proxy.com 镜像前缀，改为每项单条官方 GitHub URL（SHA256、strip、
  提交号不变）。镜像 fallback 由 CI 按 R39 自动处理：
  ci/conan/build_and_test.sh 的 "Mirror fallback" 步骤会把单值官方
  GitHub url 在构建时改写为 [gh-proxy.com, 官方] 列表；手写镜像列表
  反而会因入口正则（要求 url: 与 https:// 同行）跳过该注入（见
  DRAFT-conandata-single-url-ci-mirror-fallback）。全包复核
  notes.md/manifest.yaml/README.md/test_package 无"镜像优先"等过时
  表述，manifest.yaml 的 source/submodules URL 本就是官方地址。
- ohos_specific_test.py：check_no_rpath 现在检查 readelf 退出码，
  fail closed——readelf 执行失败（非零退出码/超时/无法解析输出）即
  该检查点判 FAIL；仅当命令成功（returncode 0）且输出中确认不存在
  RPATH/RUNPATH 时才 PASS。
- test_lci.sh：shebang 从 #!/bin/sh 改为 #!/usr/bin/env bash（与
  test_package/conanfile.py 用 bash 包装执行的调用方式一致），并加
  `set -euo pipefail`；脚本本就只用 POSIX 兼容写法 + local，在 Bash
  下合法，现有断言不降级。
- DRAFT-E565 .kv：补 `draft: true` 与 `contributor_id: AWST`（对齐
  DRAFT-E567 的草稿必需字段；技术命题不变）。
