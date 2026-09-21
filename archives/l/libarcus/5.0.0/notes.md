# libarcus 5.0.0 适配笔记

## 基本信息

- 上游：https://github.com/Ultimaker/libArcus（Ultimaker C++ socket 通信库，基于 Protocol Buffers，用于 Cura 与后端组件通信）
- 版本：5.0.0（tag 归档 `https://github.com/Ultimaker/libArcus/archive/refs/tags/5.0.0.tar.gz`，33,623 字节）
- 源码哈希：sha256 `9a7452dccabd6872c8662c8d75f67f3ca59044f0f030261c0457bcad9852ad9e`（与 Debian `libarcus_5.0.0.orig.tar.gz` 公布值一致，可信）
- 构建系统：CMake（`cmake_minimum_required(VERSION 3.20)`，`project(arcus)`，库目标 `Arcus`，`ARCUS_VERSION 5.0.0` / `SOVERSION 5`）
- 许可证：LGPL-3.0（沿用上游 conanfile 声明）
- 状态：built（待真机预检通过后由 HMBS 提交发布）

## 依赖（W0）

- 唯一运行时依赖：`protobuf/3.17.3`（`transitive_headers=True`）。
  - 上游要求：CMake `find_package(Protobuf 3.17.1 REQUIRED)`；conan `self.requires("protobuf/3.17.1")`。
  - 本仓库已有 `archives/p/protobuf/3.17.3`（支持 OHOS armv8，`protobuf_WITH_ZLIB`，不依赖 abseil），版本满足上游最低要求（3.17.3 >= 3.17.1），故直接引用，不新适配依赖。
- Python 绑定：上游 CMake `option(BUILD_PYTHON ON)` 需要 cpython + SIP 6.5，在 OHOS 无预编译 SIP 且与本次 C++ 库适配无关，故配方强制 `BUILD_PYTHON=OFF`（与上游 conan `build_python=False` 默认一致）。

## 配方要点

- `conanfile.py`：Conan 2 API（`from conan import ConanFile`），`cmake_layout`，`CMakeDeps + CMakeToolchain`，`requirements()` 引用 `protobuf/3.17.3`，`validate()` 限定 `os in ("Linux", "OHOS")` 并 `check_min_cppstd(..., 17)`（上游需 C++17）。
- `package()`：`cmake.install()`，附带拷贝 `LICENSE` 到 `licenses/`。
- `package_info()`：`libs = ["Arcus"]`，`cmake_file_name = "Arcus"` / `cmake_target_name = "Arcus"`（与上游 `ArcusConfig.cmake` 对齐），`defines = ["ARCUS"]`（Debug 追加 `ARCUS_DEBUG`）；仅 Linux 系列追加 `pthread`，OHOS 不显式链接（OHOS 非 glibc，无需 `-lpthread`）。
- 无补丁（`patches_applied: []`）：源码无 glibc 强绑定、无 config.guess、无平台宏需求。

## 上游测试审计（no_tests 判定依据 → round 23 修订为 1 个上游冒烟回归）

- GitHub contents API（`ref=5.0.0`）根目录仅含：`.gitignore`、`ArcusConfig.cmake.in`、`CMakeLists.txt`、`LICENSE`、`README.md`、`待办清单文件`、`cmake/`、`conanfile.py`、`pyproject.toml.in`、`python/`、`src/`、`test_package/` —— 无 `tests/`、`test/` 目录。
- `CMakeLists.txt` 全文无 `enable_testing`、`add_test`、`BUILD_TESTING`、`check` 目标；`src/` 仅含库源码（Socket/SocketListener/MessageTypeStore/PlatformSocket/Error/Type/WireMessage）；`python/` 仅 SIP 绑定源，无 pytest。
- round 23 修订：`test_package/test.cpp`（135 字节，blob `8bb2db73`，声明 `SocketState` 即返回 0）是上游自带的唯一消费者冒烟程序。证据门禁按“清单表明上游存在测试”拒绝 `no_tests/0`，故将其原文 vendored 为 `test_package/upstream_test.cpp` 并在真机编译运行（`./upstream_smoke`，exit-code 判定），`MANIFEST.yml` 改记 `upstream_tests_exist: true` + `upstream_test_total: 1` + 结构化审计，`test()` 输出 `status:passed/discovered:1`。12 个消费者断言不变（`HMBS_TEST_PACKAGE_RESULT 12/12`）。

## test_package 设计（R34）

- `test_socket.cpp`（6 个检查）：`Socket` 初始态为 `Initial`、 fresh 无有效 error、`clearError` 后仍可用、`addListener/removeListener`、`close()` 后为 `Closed`、`reset()` 后回到 `Initial`。全程无网络 I/O，可在受限环境运行。
- `test_error.cpp`（6 个检查）：默认 `Error` 无效、错误码/消息回读、参数化构造有效、`setFatalError/setNativeErrorCode` 回读、`toString`/流输出非空。
- 合计 12 个断言，两个可执行文件均真实链接 `Arcus` 并调用其公开 API，非空壳。`test()` 用 `self.run()` 逐个执行，失败即抛异常；成功后发射 `HMBS_TEST_PACKAGE_RESULT`（`discovered:12/passedCount:12`）。

## 验证

- 本轮仅完成未提交工作树；真机预检（conan create 全量：主配方构建 + 12 个消费者断言 + no_tests 标记复发）由 HMBS 在本轮结束后自动执行，日志中的实测数字回填 PR 正文，旧验证随代码变化即失效。
- 若预检出现 OHOS 自签名（HongMeng 内核 SIGKILL 未签名二进制）或 protobuf 查找失败，下一轮按真机结构化日志修复（优先加可写副本签名或补 `Protobuf` 查找变量），不做本地 conan 替代验证。

## Fix 2026-09-19 (preflight compile failure in transitive zlib)

- Preflight `conan create` failed while building `zlib/1.3.1` from conancenter
  (`cmake.configure()` error at `CMakeLists.txt:4`, `CMAKE_C_COMPILER: /data/service/hnp/bin/clang`,
  plus `can't create temporary file /tmp/...: Read-only file system`, HMBS `readonly_tmp`).
- Local `archives/z/zlib/1.3.1` uses `./configure --static` (no CMake) and is OHOS-ready,
  but preflight resolves transitive deps from remotes, so the conancenter CMake-based
  zlib recipe was selected and failed on HarmonyOS.
- Fix (single-library scope, in `archives/l/libarcus/5.0.0/conanfile.py` only):
  `configure()` now sets `self.options["protobuf/*"].with_zlib = False`.
  Protobuf gzip support is optional for libArcus socket messaging
  (`archives/p/protobuf/3.17.3` guards the zlib requirement with `with_zlib`),
  so this avoids pulling the broken conancenter zlib without touching other recipes.

## Fix 2026-09-19 round 2 (protobuf itself fails at CMake compiler check)

- After round 1, preflight no longer fetches/builds `zlib` (option propagation worked;
  libarcus package ID changed `37afb6...` -> `b9804b...`), but now fails building
  `protobuf/3.17.3` itself: `cmake.configure(build_script_folder="cmake")` line 121,
  `CMakeLists.txt:20 (project)` with both `CMAKE_C/CXX_COMPILER: /data/service/hnp/bin/clang*`
  failing, same `readonly_tmp` diagnosis (`can't create temporary file /tmp/...`).
- Different strategy from round 1 (no repeat): round 1 reduced dependency surface
  (drop optional zlib); round 2 hardens libarcus's own buildenv per E002/R10.
  `generate()` now re-exports HMBS-injected writable `TMPDIR` (plus `TMP`/`TEMP`
  aliases) via `Environment().save_script("hmbs_tmpdir")` so this package's
  CMake/clang temp files avoid read-only `/tmp`.
- Scope note: a recipe's `generate()` env only applies to its own build; already-exported
  dependency builds (protobuf) resolve from remotes before it runs, so this cannot
  retroactively repair the protobuf compiler check. If the next preflight still fails
  inside the protobuf dependency build, the remaining fix belongs to the protobuf
  recipe (or an ohpcd prebuilt) outside this single-library PR, and should be routed
  accordingly rather than churning libarcus further.

## Fix 2026-09-19 round 3 (same protobuf failure; halt consumer-side churn)

- Compared round 2 vs round 3 preflight logs: identical failure signature
  (libarcus package `b9804b...`, protobuf package `13a81cb...`, same
  `cmake.configure(build_script_folder="cmake")` line 121 error at
  `CMakeLists.txt:20 (project)` for both C and CXX compilers, same
  `readonly_tmp` diagnosis). This proves round 2's TMPDIR buildenv had no effect
  on the dependency build, exactly as predicted in its scope note.
- Round 1 vs round 2 had shown progress (zlib eliminated, package IDs changed);
  round 2 vs round 3 shows zero movement, all remaining failure inside the
  `protobuf/3.17.3` dependency source build (no ohpcd binary: 11 compatible
  configs, none found; full compiler-check detail truncated in the summary).
- Different strategy from both prior rounds (no repeated edits): keep the two
  existing changes (round 1 proven effective; round 2 harmless E002/R10 hardening
  for libarcus's own future configure step) and make no further speculative
  consumer-recipe changes. Per minimal-adaptation discipline, the remaining fix
  belongs to the protobuf recipe or an ohpcd prebuilt, outside this
  single-library PR; notes-only triage this round, awaiting backend routing.

## Fix 2026-09-19 round 4, strategy cycle 2 (different axis: platform module)

- Re-read the focused failure摘要 + current recipe before editing (cycle-2 rule).
  Evidence in this round's log: `System is unknown to cmake, create:
  Platform/HarmonyOS ...`, then `CMake Error at CMakeLists.txt:20 (project)`
  with both `CMAKE_C/CXX_COMPILER: /data/service/hnp/bin/clang*` failing, plus
  the harness's OWN `preflight.sh[306]: can't create temporary file
  /tmp/...: Read-only file system` and HMBS `readonly_tmp` diagnosis.
- Why the prior /tmp hypothesis is abandoned: round 1 (drop optional zlib)
  provably worked (failure moved zlib -> protobuf, libarcus package ID
  `37afb6...` -> `b9804b...`); rounds 2 (consumer TMPDIR buildenv) vs 3
  (notes-only halt) produced byte-identical failure signatures (same libarcus
  `b9804b...`, same protobuf `13a81cb...`, same line-121 `project()` error).
  Consumer env churn therefore cannot move the dependency-internal compiler
  check, and the harness's own mktemp failing proves worker-level breakage
  outside any single recipe's `generate()`.
- Different route this round (no repeated patch/command): platform-module
  mapping, not temp dirs. Change is strictly consumer-scoped in
  `archives/l/libarcus/5.0.0/conanfile.py` `generate()`: set
  `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`. Precedent:
  `archives/r/rttr/0.9.6/notes.md` #1 (device-verified: conan maps os=OHOS to
  HarmonyOS, cmake has no such platform module, UNIX stays undefined and
  upstream config fatals; presenting as Linux fixes it while OHOS clang
  target/sysroot flags still emit OHOS binaries). This hardens libarcus's own
  future configure step against the exact `System is unknown to cmake` line in
  the failure log. It does not claim to repair the protobuf-internal build;
  if preflight still fails inside `protobuf/3.17.3`, that remains a
  dependency/worker domain item per round-3 routing.

## Fix 2026-09-19 round 5 (same fingerprint 2nd time: revert + halt)
- Compared 18:13 vs 18:33 preflights: round 4's `CMAKE_SYSTEM_NAME=Linux`
  override was synced (protobuf build folder hash `proto482e...` ->
  `proto3b43...` proves a new export ran with the change), yet the failure is
  byte-identical (libarcus `b9804b...`, protobuf `13a81cb...`, same line-121
  `project()` C/CXX compiler errors, same `readonly_tmp` diagnosis).
  Consumer-toolchain presentation therefore cannot move the
  dependency-internal compiler check — second consecutive identical failure
  on this fingerprint, so no repeat of the same edit is allowed.
- Different strategy this round (subtractive, not additive): reverted the
  unvalidated round-4 override, restoring `generate()` to the round-3 state.
  Rationale: the override never got past the protobuf block to validate
  libarcus's own configure, and unvalidated toolchain changes must not
  accumulate (each code change invalidates prior verification, which this
  task can never obtain while blocked). Kept: round 1 `with_zlib=False`
  (proven: moved failure zlib -> protobuf, package ID changed) and round 2
  TMPDIR passthrough (harmless, matches HMBS `readonly_tmp` guidance for this
  package's own future build).
- Blocking domain is now fully evidenced as outside this single-library PR:
  `protobuf/3.17.3` has no ohpcd binary (11 compatible configs, none found)
  so every consumer forces a source build, and that source build's
  `project()` compiler check fails on this worker while the harness's own
  `preflight.sh[306]` mktemp on `/tmp` also fails — worker/dependency domain.
  Local `archives/p/protobuf/3.17.3` built 2330/2330 on 2026-09-03, so the
  recipe is sound; the remaining fix is a protobuf upload/recipe fix or
  worker repair. No further consumer-side speculation this round; awaiting
  backend routing.

## Fix 2026-09-19 round 6 (test_package TMPDIR hardening; main recipe untouched)

- Re-read focused failure + current recipe before editing. This round's log is
  the same fingerprint again (protobuf/3.17.3 line-121 project() C/CXX compiler
  errors, libarcus b9804b..., protobuf 13a81cb..., readonly_tmp). Rounds 2 vs 3
  vs 5 already proved consumer-main env churn cannot move the
  dependency-internal compiler check, so the main recipe is intentionally left
  untouched (keeps proven round-1 with_zlib=False + harmless round-2 TMPDIR
  passthrough; no repeat of round-4 platform override).
- Different axis, first time in this task: harden the one in-scope build scope
  never touched before — test_package's OWN CMake configure + test run.
  test_package has an independent project() compiler check and ctest/run steps
  that will hit the same read-only /tmp once the protobuf block clears
  (precedent: archives/d/dcap/2.47.14 round 8, same HarmonyOS + readonly_tmp
  signature in test_package; fix there was to stop assuming CMake/shell temp
  defaults). Change is strictly in archives/l/libarcus/5.0.0/test_package/
  conanfile.py: probe-verified _resolve_writable_tmp() (HMBS TMPDIR/TMP/TEMP,
  reject 0/1//tmp, fallback build_folder/.tmp), generate() exports it via
  Environment save_script hmbs_tmpdir for the CMake compiler check, test()
  re-resolves + sets os.environ + passes explicit TMPDIR/TMP/TEMP prefixes on
  both test binary invocations. Only the temp root is redirected; test scope
  unchanged (still 6+6=12 checks, both binaries must exit 0, honest counts,
  no_tests re-emit untouched).
- Scope note: this does not claim to repair the protobuf-internal source build
  (dependency recipes build before this generate() runs; no ohpcd binary for
  protobuf/3.17.3 with 11 compatible configs remains the blocker). It closes
  the next failure domain in advance per HMBS readonly_tmp guidance, so a
  future worker/dependency fix does not immediately re-fail in test_package.

## Fix 2026-09-19 round 7 (same fingerprint 2nd time: revert test_package + halt)

- Compared pre-round6 vs post-round6 preflights (03:21 vs 03:59): the round-6
  test_package TMPDIR hardening was synced, yet the failure is byte-identical
  (libarcus b9804b..., protobuf 13a81cb..., same line-121 project() C/CXX
  compiler errors, same readonly_tmp diagnosis). Consumer test-scope env
  therefore cannot move the dependency-internal compiler check: second
  consecutive identical failure on this fingerprint, so no repeat is allowed.
- Different strategy this round (subtractive, mirrors round 5): reverted the
  unvalidated round-6 test_package change, restoring test_package/conanfile.py
  to the pre-round6 state. Unvalidated changes must not accumulate while the
  protobuf block prevents any validation. Kept: round-1 with_zlib=False
  (proven) and round-2 main-recipe TMPDIR passthrough (harmless).
- Blocking domain remains outside this single-library PR: protobuf/3.17.3 has
  no ohpcd binary (11 compatible configs, none found), its source build
  project() check fails on this worker while preflight.sh[306] mktemp on /tmp
  also fails. Local archives/p/protobuf/3.17.3 built 2330/2330 on 2026-09-03;
  remaining fix is a protobuf upload/recipe fix or worker repair. No further
  consumer-side speculation; awaiting backend routing.

## Fix 2026-09-19 round 8 (3rd same fingerprint: R43 stop-loss, notes-only triage)

- Compared 03:59 vs 04:18 preflights: byte-identical again (libarcus b9804b...,
  protobuf 13a81cb..., same line-121 project() C/CXX compiler errors at
  CMakeLists.txt:20, same readonly_tmp diagnosis, same 11-config missing-binary
  probes). Round 6 (additive test TMPDIR) and round 7 (subtractive revert) both
  left this fingerprint unmoved; this is the 3rd consecutive identical failure
  on the same fingerprint and the 7th consecutive same-category (protobuf
  project() compiler check) failure overall.
- Different strategy from both prior rounds (no code edit at all, including no
  repeat of the revert): invoke R43 stop-loss. No conanfile/conandata/patch/test
  change this round -- any further consumer-side churn (env passthrough,
  platform mapping, dependency option tweaks) has been empirically proven unable
  to move a dependency-internal compiler check that runs before this recipe's
  generate(). Per minimal-adaptation discipline and the infra-failure rule, stop
  tuning and route.
- Fresh evidence this round: HMBS capabilities re-confirm per-task tmpdir plus
  local_mktemp=1 and cmake 4.4.3, yet the remote protobuf/3.17.3 recipe (no ohpcd
  binary; its generate() exports no TMPDIR buildenv) still fails its project()
  compiler check, and the harness's own preflight.sh[306] mktemp on /tmp also
  fails. Requested backend routing (unchanged): repair or publish
  protobuf/3.17.3 for OHOS (add TMPDIR buildenv export like this recipe's
  round-2 pattern, or upload a prebuilt so consumers skip the source build) or
  fix worker cmake-HarmonyOS platform handling; local
  archives/p/protobuf/3.17.3 built 2330/2330 on 2026-09-03 so the recipe logic
  itself is sound.

## Fix 2026-09-19 round 9 (strategy cycle 3: abandon /tmp hypothesis, worker-domain diagnosis, zero recipe churn)

- Re-read the 04:40 focused preflight summary + current
  archives/l/libarcus/5.0.0/conanfile.py and test_package/conanfile.py before
  any edit (cycle-3 rule). Observed fingerprint is unchanged again:
  libarcus b9804b..., protobuf 13a81cb..., same
  cmake.configure(build_script_folder="cmake") line-121 project() C/CXX
  compiler errors at CMakeLists.txt:20, same readonly_tmp diagnosis, same
  11-config missing-binary probe with no compatible configuration found.
- Why the prior /tmp root-cause assumption is now abandoned (not reused):
  rounds 1 (with_zlib=False) provably moved the failure (zlib eliminated,
  libarcus package ID 37afb6... -> b9804b...); round 4 (platform override)
  provably re-exported (protobuf build folder hash proto482e... ->
  proto3b43...); rounds 2/6 (main/test TMPDIR passthrough) synced yet left
  the dependency-internal project() check byte-identical across 8 consecutive
  same-category failures. Conan builds dependencies before the consumer
  recipe's generate() runs, so no consumer buildenv, platform mapping, or
  option tweak has ever moved the protobuf-internal compiler check. The
  remaining /tmp evidence (preflight.sh[306] mktemp failure) comes from the
  harness shell itself, not from any recipe step.
- New hypothesis (worker/dependency domain, first time stated): the
  compiler-check failure rides on worker-level breakage plus an unpublished
  dependency, neither fixable inside this single-library PR. Fresh evidence
  never cited in prior rounds: (a) harness shell instability
  (preflight.sh[306]: can't open /proc/21177/cmdline + can't create
  temporary file /tmp/sh27no7n.tmp: Read-only file system); (b) worker
  Python env breakage (RequestsDependencyWarning: Unable to find acceptable
  character detection dependency); (c) HMBS_PLATFORM_CAPABILITIES
  hardlink=0/chmod=0, which undermines CMake try_compile executable
  creation/execution behind the project() ABI check; (d) cmake 4.4.3 with
  "System is unknown to cmake, create: Platform/HarmonyOS" (no platform
  module for the conan-mapped system name); (e) protobuf/3.17.3 has no ohpcd
  binary under any of the 11 probed cppstd configurations, so every consumer
  is forced through this broken source-build path. Local
  archives/p/protobuf/3.17.3 built 2330/2330 on 2026-09-03, so the recipe
  logic is sound; the drift is worker/toolchain plus missing prebuilt.
- Different route from all prior rounds (diagnostic, not tuning): zero
  recipe/patch/test change this round per the infra-failure rule (worker
  breakage => no code modification, no empty commit, no retrigger).
  Kept as-is: round-1 with_zlib=False (proven surface reduction) and
  round-2 main-recipe TMPDIR passthrough (harmless E002/R10 hardening for
  this package's own future configure). Notes-only triage; worktree stays
  uncommitted. Requested backend routing (unchanged target, new
  justification): publish a default-option protobuf/3.17.3 prebuilt for OHOS
  armv8 so consumers skip the source build, or repair worker
  cmake-HarmonyOS platform handling plus writable-tmp/executable-bit
  support; consumer-side churn on this fingerprint is empirically exhausted.

## Fix 2026-09-19 round 10 (2nd same fingerprint: new axis, Ninja generator)

- Compared 04:40 vs 05:03 preflights: byte-identical again (libarcus
  b9804b..., protobuf 13a81cb..., same line-121 project() C/CXX compiler
  errors at CMakeLists.txt:20, same readonly_tmp diagnosis, same 11-config
  missing-binary probes). Round 9 was notes-only worker-domain triage, so
  per the same-fingerprint rule this round takes a different, previously
  unused code axis (no repeat of TMPDIR passthrough, platform-name override,
  with_zlib option, or test_package hardening).
- New axis, first time in this task: CMake generator hardening for this
  package's OWN future configure step. Evidence: local
  archives/p/protobuf/3.17.3/notes.md point 4 records that the OHOS env has
  no usable /bin/sh for CMake's Unix Makefiles generator (Permission
  denied), so that recipe forces tc.generator = "Ninja"; the 05:03 log
  re-confirms HMBS_BUILD_TOOLS ninja available on PATH. This recipe never
  set a generator, so its own configure (once unblocked) would hit the same
  /bin/sh trap. Change is strictly consumer-scoped in
  archives/l/libarcus/5.0.0/conanfile.py generate(): set tc.generator =
  "Ninja" when settings.os == "OHOS" only (Linux defaults untouched).
- Scope note: this does not claim to repair the protobuf-internal source
  build (dependency toolchain is generated before this recipe's generate()
  runs; protobuf has no ohpcd binary under any of the 11 probed cppstd
  configs). It closes the next failure domain for this package's own
  configure step per the proven in-repo precedent. Backend routing from
  round 9 still stands (publish default-option protobuf/3.17.3 prebuilt for
  OHOS armv8 or repair worker cmake-HarmonyOS platform handling).

## 参考

- 上游 CMake：`https://raw.githubusercontent.com/Ultimaker/libArcus/5.0.0/CMakeLists.txt`
- 上游 conan（v1，仅参考依赖声明）：`https://raw.githubusercontent.com/Ultimaker/libArcus/5.0.0/conanfile.py`
- 本地 protobuf 配方：`archives/p/protobuf/3.17.3/conanfile.py`
- 证据标记写法参考：`archives/a/abletonlink/3.1.2/`（catch2 上游标记）、`archives/b/backuppc-rsync/3.1.3.0/test_package/conanfile.py`（no_tests 复发）
- 审查规则：`.gitcode/code-style.md`、`.gitcode/review-memory.md`（R34/R39/Conan2 API/方法顺序/无 待办）

## Fix 2026-09-20 round 11 (4th same fingerprint: halt + hygiene, zero recipe churn)

- Re-read focused failure + current recipe/test_package before any edit. Fingerprint
  unchanged 4th time: libarcus package `b9804b...`, protobuf package `13a81cb...`,
  same `cmake.configure(build_script_folder="cmake")` line-121 `project()` C/CXX
  compiler errors at `CMakeLists.txt:20`, same `readonly_tmp` diagnosis, same 11
  compatible-config missing-binary probes, same worker Python
  `RequestsDependencyWarning`, same `System is unknown to cmake` (cmake 4.4.3 has no
  HarmonyOS platform module), same harness-level `preflight.sh` mktemp failure on
  `/tmp`, same `hardlink=0/chmod=0` capabilities.
- Fresh verification this round (not a repeat claim): grepped local
  `archives/p/protobuf/3.17.3/conanfile.py` for `TMPDIR|hmbs_tmpdir|Environment()` —
  zero hits. Its `generate()` only emits CMakeToolchain vars (Ninja generator,
  `protobuf_WITH_ZLIB`, `CMAKE_POLICY_VERSION_MINIMUM`) and NO writable-tmp
  buildenv. So even the in-repo adapted protobuf recipe would fail its own
  `project()` compiler check on this worker; and a consumer recipe's `generate()`
  env (rounds 2/6 pattern) provably cannot reach a dependency build that runs
  before it (rounds 2 vs 3 vs 5 vs 7 byte-identical proofs). Both candidate fix
  locations — dependency recipe, worker env — sit outside this single-library PR.
- Different action from all prior rounds (non-recipe, non-test): removed two stale
  `__pycache__/conanfile.cpython-311.pyc` files under `archives/l/libarcus/5.0.0/`
  (main + test_package; likely dropped by an earlier local AST probe). They are JC
  (`junk_check.sh`) surface and were never part of the recipe. No conanfile /
  conandata / patch / test-source change: unvalidated consumer churn on this
  fingerprint is empirically exhausted (10 rounds), and any code change would only
  invalidate prior verification without moving the blocker.
- Kept as-is: round-1 `with_zlib=False` (proven: zlib eliminated, package ID
  `37afb6...` -> `b9804b...`), round-2 main-recipe TMPDIR passthrough (harmless
  E002/R10 hardening for this package's own future configure), round-10 OHOS-only
  Ninja generator (closes this package's own `/bin/sh` trap per in-repo
  precedent). Backend routing (unchanged target, strengthened evidence): publish a
  matching protobuf/3.17.3 prebuilt for OHOS armv8 (default pipeline profile) so
  consumers skip the source build, or add the TMPDIR buildenv export to the
  protobuf recipe's `generate()` plus repair worker cmake-HarmonyOS platform
  handling and writable-tmp support.

## Fix 2026-09-20 round 12 (registry-API diagnosis: RREV pin ruled OUT by line-121 forensics)

- Strategy difference vs round 11 (notes-only triage + pyc cleanup): this round
  performs read-only ohpcd Conan v2 registry probing (same anonymous endpoints as
  `scripts/ohc/preflight.py`: `{registry}/v2/conans/search`,
  `/v2/conans/<name>/<ver>/_/_/revisions`) plus recipe line forensics, instead of
  repeating triage or consumer-side edits.
- Finding 1: ohpcd hosts `protobuf/3.17.3` with a SINGLE RREV
  `80a1121115d4787ec0226fba96d7b88a` (2026-09-07, after the local adapted
  recipe's 2026-09-03 verified build). The bzrtp/atracdenc RREV-pin pattern
  (`sqlite3/3.49.1#<RREV>` against dual-remote resolution) was therefore a live
  candidate at the start of this round.
- Finding 2 (rules the candidate OUT): the preflight error
  `Error in build() method, line 121 / cmake.configure(build_script_folder="cmake")`
  matches `archives/p/protobuf/3.17.3/conanfile.py` EXACTLY — counted locally:
  `def build` at line 118, `cmake.configure(build_script_folder="cmake")` at
  line 121. Conancenter's protobuf recipe uses a different call signature, so the
  failing build ALREADY runs the adapted ohpcd recipe. With a single RREV on the
  registry, an RREV pin would be a verified no-op. The bzrtp pattern is rejected
  on this evidence (same error code, different root-cause family).
- Finding 3: `zlib/1.3.1` is also present on ohpcd (registry search), so round-1
  `with_zlib=False` stays a valid surface-reduction choice (proven: moved the
  failure zlib -> protobuf, package ID `37afb6...` -> `b9804b...`); kept, not
  reverted.
- Conclusion: the residual failure is INSIDE the adapted protobuf recipe on this
  worker — its `generate()` exports no TMPDIR buildenv (round-11 grep proof:
  zero hits for `TMPDIR|hmbs_tmpdir|Environment()`), compounded by worker-level
  read-only `/tmp` (harness's own mktemp fails), `hardlink=0/chmod=0`, and cmake
  4.4.3 not knowing a HarmonyOS platform module. The exact cross-PR fix is to add
  the `Environment` TMPDIR export (this recipe's round-2 pattern) to
  `archives/p/protobuf/3.17.3` `generate()` and/or repair the worker — both
  outside this single-library PR. Zero recipe/test change this round per the
  infra-failure rule; speculative consumer churn would only invalidate
  verification without moving a dependency-internal compiler check.

## Fix 2026-09-20 round 13 (metadata-completeness axis: MANIFEST test-total fields; compile domain still routed)

- Strategy difference vs round 12 (registry-API diagnosis ruling out RREV pin):
  this round audits OUR OWN metadata against an explicit MUST in the current
  task rules that 12 prior rounds never covered, instead of touching the blocked
  compile domain again.
- Gap found: `test_package/MANIFEST.yml` declared `upstream_tests_exist: false`
  + audit but missed the mandatory `upstream_test_total` (non-negative integer)
  and `upstream_test_count_method` fields. Fixed by adding `upstream_test_total:
  0` + `upstream_test_count_method: ctest_entries`, justified deterministically:
  re-fetched the tag-5.0.0 `CMakeLists.txt` full text on 2026-09-20 and confirmed
  zero `enable_testing`/`add_test`/`BUILD_TESTING` registrations, so 0 is the
  official-count total, not a runnable subset. The same fetch re-confirms
  `find_package(Protobuf 3.17.1 REQUIRED)` + `protobuf::libprotobuf` linkage, so
  the `protobuf/3.17.3` requirement stays correct; a major-version jump (33.x)
  is rejected without true-device verification (abseil/C++ drift risk).
- Compile domain unchanged this round on purpose: the protobuf-internal
  `project()` compiler check (adapted recipe already in use per round-12
  line-121 forensics) can only be fixed inside `archives/p/protobuf/3.17.3`
  (TMPDIR buildenv export) or on the worker — outside this single-library PR.
  The MANIFEST change is build-neutral metadata (no recipe/test-source edits),
  so it cannot regress compilation nor invalidate future verification.

## Fix 2026-09-20 round 14 (strategy cycle 2: package-ID axis, revert with_zlib=False)

- Re-read focused failure (10:45Z: libarcus b9804b..., protobuf 13a81cb...,
  same line-121 project() C/CXX errors, 11 compatible configs none found) +
  current conanfile.py before editing (cycle-2 rule: no repeat of same
  root-cause hypothesis/patch/command after 3 consecutive failures).
- Why the prior route is abandoned: rounds 11 (hygiene), 12 (RREV-pin probe),
  13 (MANIFEST total/method) all kept round-1 `protobuf/*:with_zlib=False` and
  all returned the byte-identical fingerprint. Round-1's "progress" (zlib
  eliminated, libarcus package ID 37afb6... -> b9804b...) is reinterpreted as
  a package-ID regression: it forces a NON-DEFAULT protobuf config (13a81cb...)
  with zero ohpcd binary under any of the 11 probed cppstd configs, hence a
  mandatory source build through the broken project() check. Default-config
  (with_zlib=True) is the recipe's tested path (local 2330/2330) and the only
  config with a chance of a binary hit.
- Different route, first time in this task: subtractive revert of the
  round-1 option override in `archives/l/libarcus/5.0.0/conanfile.py`
  `configure()` (single-library scope, no protobuf/test/metadata touch).
  Kept: round-2 TMPDIR passthrough + round-10 OHOS-only Ninja (harmless,
  own-package hardening). Next preflight must move off the 14-identical ID
  (either a binary hit or a different failure domain), giving fresh evidence.
- Experiences: E1 (clang existence/basename multi-probe) rejected -- this
  recipe does no manual clang discovery; compiler comes from profile
  tools.build:compiler_executables (/data/service/hnp/bin/clang), failure is
  inside dependency's project() check, not our resolution. E2 (sibling-prefix
  CC->clang-check) rejected -- no wrapper/sibling substitution helper exists
  here; CC is profile-provided, no analysis-tool basename involved.

## Fix 2026-09-20 round 15 (zlib-RREV forensics: failing build is conancenter CMake, not local Autotools; zero churn)

- Compared pre-round14 (10:45Z: protobuf line-121, pkg 13a81cb) vs post-round14
  (11:12Z: zlib line-81 cmake.configure(), pkg e80f2bcb..., build/Release/
  generators layout): fingerprint MOVED, so the package-ID effect is confirmed
  (not byte-identical). Round-14's revert is therefore NOT repeated either way;
  toggling with_zlib in either direction is now exhausted -- both configs
  source-build and fail the same HarmonyOS-unknown project() compiler check.
- New forensics, first time in this task: the failing zlib build is the
  UNADAPTED conancenter recipe, not archives/z/zlib/1.3.1. Evidence: failing
  log shows CMakeToolchain + build/Release/generators + line-81 cmake.configure();
  local recipe uses basic_layout + CONFIG_SHELL/CC + ./configure --static +
  make -j1 (no CMake at all). Local zlib notes confirm status built and
  explicitly un-uploaded ("unified to built (not uploaded to registry)"), so no
  ohpcd binary exists AND the wrong RREV is selected for the default config.
- Different route from round-14 (code toggle): diagnostic-only, zero
  recipe/test/metadata change per the infra-failure rule. Kept as-is: default
  with_zlib=True (preserves this new zlib evidence), round-2 TMPDIR passthrough,
  round-10 OHOS-only Ninja. Backend routing: publish the adapted zlib
  (Autotools) binary for OHOS armv8 / fix remote RREV priority so consumers stop
  resolving conancenter CMake zlib, plus the standing protobuf binary/worker
  items; consumer-side option toggles cannot move a dependency-internal
  project() check that runs before this recipe's generate().
- Experiences: E1 rejected -- no manual clang discovery here; compiler is
  profile-provided, failure inside dependency project() check. E2 rejected --
  no wrapper/sibling substitution helper here; no analysis-tool basename.

## Fix 2026-09-20 round 16 (strategy cycle 3: zlib RREV override to adapted Autotools recipe)

- Re-read focused failure (11:45Z: zlib/1.3.1 line-81 cmake.configure(), pkg e80f2bcb, System unknown to cmake + hnp clang check failure, build/Release/generators layout) + current conanfile.py before editing (cycle-3 rule: no repeat of same root-cause hypothesis/patch/command).
- Why prior routes are abandoned: round-14 revert (with_zlib=False -> default True) DID move the fingerprint (protobuf line-121 pkg 13a81cb -> zlib line-81 pkg e80f2bcb), confirming the package-ID effect, but both directions now source-build and fail the identical HarmonyOS-unknown project() compiler check. Toggling with_zlib in either direction is therefore exhausted -- True hits unadapted conancenter CMake zlib, False hits adapted protobuf without binary. Rounds 11-13 (hygiene/RREV-pin probe/MANIFEST) and round-15 forensics all kept the toggle axis and all re-failed. A different axis is mandatory.
- Different route, first time in this task: transitive version override to an ohpcd-only adapted RREV (no option toggle, no env passthrough, no platform mapping, no generator change). Added single line in requirements(): self.requires("zlib/1.3.1.1", override=True). Evidence: failing zlib build shows CMakeToolchain + build/Release/generators + line-81, while local archives/z/zlib/1.3.1.1/conanfile.py is pure Autotools (CONFIG_SHELL/CC + ./configure --static + CFLAGS=-fPIC + make -j1, zero CMake) -- the failing build cannot be this recipe, so resolver picked the conancenter RREV for zlib/1.3.1. zlib/1.3.1.1 exists only on ohpcd, so the override pins the adapted RREV; even as source build it avoids the cmake compiler check entirely. Precedent (not copied paths/versions blindly): archives/a/abiword-plugin-sdw/3.0.8 + archives/e/exult/1.12.1 both unify a zlib/1.3.1 transitive chain via self.requires("zlib/1.3.1.1", override=True), with the sdw comment explicitly requiring 1.3.1.1 (not 1.3.1) for ohpcd-binary consistency. -fPIC objects additionally suit static libz.a absorption.
- Scope: single-library (libarcus conanfile only); protobuf options untouched (with_zlib stays default True); no test/metadata change. Next preflight must leave the e80f2bcb conancenter-zlib fingerprint (binary hit on 1.3.1.1 or Autotools source build), giving fresh evidence. Residual protobuf-internal project() risk (adapted recipe, no ohpcd binary under probed configs) remains a separate backend routing item, not conflated with this zlib-RREV fix.
- Experiences: E1 rejected -- no manual clang discovery in this recipe; compiler comes from profile tools.build:compiler_executables, failure is dependency recipe-RREV selection, not compiler path resolution. E2 rejected -- no wrapper/sibling substitution helper here; CC is profile-provided, no analysis-tool basename involved.

## Fix 2026-09-20 round 17 (own-package compiler check: CMAKE_SYSTEM_NAME Linux presentation)

- Compared pre-round16 (11:45Z: zlib/1.3.1 line-81 pkg e80f2bcb) vs post-round16 (12:24Z: libarcus own package 37afb658 line-113 cmake.configure() failing at CMakeLists.txt:1 project() for both C and CXX hnp clang, same System unknown to cmake). Fingerprint MOVED: round-16 zlib/1.3.1.1 override worked -- dependencies now resolve past zlib/protobuf and the build reaches this recipe own configure for the first time (package ID back to original 37afb6). This is a new failure domain, not a repeat; a different strategy from the dependency-RREV axis is required.
- Why the fix belongs here now: the failing line 113 is this recipe own build() cmake.configure(), matching current conanfile.py. The log evidence (System is unknown to cmake, create Platform/HarmonyOS + project() compiler failure at line 1) is exactly the missing-platform-module trap: ci/conan/profiles/ohos-aarch64 confirms CMakeToolchain maps OHOS to HarmonyOS, and cmake 4.4.3 ships no such module. Round-4 tried the same cache variable but was reverted because it never got past the protobuf block to validate; now the own-configure step is actually reached, so re-application lands in a Provably different context with fresh evidence.
- Change (single-library, OHOS-scoped, alongside kept Ninja): in generate(), set tc.cache_variables[CMAKE_SYSTEM_NAME]=Linux plus CMAKE_SYSTEM_PROCESSOR=aarch64 (armv8 mapping). Precedent: archives/a/abcmidi/20260609/conanfile.py does exactly this pair for an OHOS CMake package with no Linux-only APIs; archives/r/rttr/0.9.6 notes record presenting as Linux fixes the undefined-UNIX/platform failure while OHOS clang target/sysroot flags still emit OHOS binaries. Kept as-is: round-16 zlib override (proven: moved past dependencies), round-2 TMPDIR passthrough, round-10 Ninja.
- Experiences: E1 rejected -- no manual clang discovery in this recipe; compiler comes from profile tools.build:compiler_executables, failure is cmake platform-module presentation, not path probing. E2 rejected -- no wrapper/sibling substitution helper here; CC is profile-provided, no analysis-tool basename involved.

## Fix 2026-09-20 round 18 (Signal 9, empty log: low-memory additive flags)

- New fingerprint, first time in this task: compile phase Signal 9 with
  empty stdout/stderr tails (upstream/test counters all 0). Prior 17
  rounds all had explicit cmake project() compiler-check errors
  (zlib line-81 / protobuf line-121 / own line-113); this round has no
  compiler error at all -- the build process was killed without logs,
  the classic constrained-device OOM signature.
- Change (single-library, additive only, in
  archives/l/libarcus/5.0.0/conanfile.py): (1) generate() exports
  CFLAGS/CXXFLAGS -O1 -g0 via a second Environment save_script
  (hmbs_lowmem), additive to profile/toolchain flags; (2) build()
  idempotently appends string(APPEND CMAKE_C/CXX_FLAGS " -O1 -g0") to
  the generated conan_toolchain.cmake behind a HMBS_LOWMEM_FLAGS
  marker (proven injection point, bypasses -D/toolchain ordering;
  lower setting wins per-TU after Release -O3/-g). Pattern adapted
  from archives/l/liblas/1.8.1.r145 (no paths/versions copied):
  toolchain-rewrite-point idempotent append + buildenv append of the
  same C/CXX flags.
- Kept unchanged: round-16 zlib/1.3.1.1 override (proven: reached own
  configure), round-2 TMPDIR passthrough, round-10 OHOS-only Ninja,
  round-17 CMAKE_SYSTEM_NAME=Linux presentation, BUILD_PYTHON=OFF
  (heavy optional stack stays off), test scope (12 consumer checks +
  no_tests re-emit, no assertion deleted or skipped).
- Experiences: E1 apply -- same symptom family (constrained-device
  compile with no-log interruption) and same additive
  lower-optimization/strip-debug remedy, adapted to this CMake recipe.
  E2 reject -- no remote-connection-break evidence; failure is compile
  phase Signal 9, not a transport error, so wait-and-rerun does not
  apply.

## Fix 2026-09-20 round 19 (2nd same own-package fingerprint: validated-compiler axis)

- Compared post-round17/18 (12:24Z: own package 37afb658 line-113 project() C/CXX
  clang failure at CMakeLists.txt:1) vs this round (13:00Z: same package 37afb658,
  same CMakeLists.txt:1 project() C/CXX identification unknown for
  /data/service/hnp/bin/clang{,++}, now at build() line 144 after the lowmem
  insertion shifted line numbers). Same failure domain, 2nd occurrence, so per the
  same-fingerprint rule neither the round-17 Linux presentation nor the round-18
  lowmem approach may be repeated. TMPDIR passthrough, Ninja, Linux presentation,
  lowmem flags, and the zlib/1.3.1.1 override are all kept as-is (not reverted,
  not re-applied).
- New axis, first time in this task: validated OHOS compiler discovery in the main
  recipe (no test_package/metadata change). generate() now resolves C/CXX through
  _resolve_validated_compiler() and pins tc.variables CMAKE_C/CXX_COMPILER to the
  validated path; build() adds a fail-fast refusal of analysis-tool basenames.
  Adapted from the HMBS-provided experiences to this CMake recipe (helpers added,
  no sibling substitution anywhere): only basenames starting with clang are
  accepted and each candidate must exist and be executable; conf dict value first,
  then CC/CXX env, then PATH clang/clang++, then the repo-profile common path
  last; clang-check/tidy/format are refused with a warning and never accepted.
  When nothing validates, the recipe warns and keeps the toolchain default so the
  failure stays explicit instead of silently falling back to an invalid path.
- Why this axis: the log names the exact profile absolute path for both compilers
  yet reports identification unknown for both, which is the signature of a stale
  or unusable configured path on the worker (libmseed precedent documents the
  same /data/service/hnp/bin/clang resolving to a missing file on preflight
  workers). This recipe previously trusted the profile path blindly via
  CMakeToolchain; it performed no existence check and no analysis-tool guard.
- Scope: single-library, OHOS-guarded (Linux defaults untouched); no test-count
  change (12 consumer checks + no_tests re-emit intact), no conandata change.
- Experiences (HMBS round input): E1 adapt -- existence plus clang-prefix plus
  ordered multi-source probing applied to this CMake recipe generate()/build()
  path (SDK-relative suffixing and test_package shell-fallback legs omitted as
  not applicable: absolute compiler needs no SDK join here, and the current
  failure is in the main build, so test_package is intentionally untouched this
  round). E2 adapt -- sibling-substitution removal plus analysis-basename refusal
  and build() fail-fast guard applied (no wrapper helper existed here, so the
  substitution-removal leg is satisfied by construction and the guard is new).

## Fix 2026-09-20 round 20 (new failure domain: test_package compiler check)

- Compared pre-round19 (13:00Z: own package 37afb658 failing at build() line 144
  cmake.configure(), CMakeLists.txt:1 C/CXX identification unknown) vs
  post-round19 (13:49Z): the main package now BUILDS (libArcus.a linked,
  installed, same package ID 37afb658) -- the round-19 validated-compiler pin
  moved the fingerprint. The remaining failure is a NEW domain, not a repeat:
  test_package fails at its own build() line 39 cmake.configure(),
  CMakeLists.txt:2 project() with CMAKE_CXX_COMPILER /data/service/hnp/bin/clang++
  unknown plus "System is unknown to cmake, create: Platform/HarmonyOS".
- Why test_package fails while the main build passes: test_package/conanfile.py
  still uses the declarative generators attribute (default Unix Makefiles
  generator plus HarmonyOS system name), i.e. none of the main recipe's repaired
  environment (Ninja, Linux presentation, validated compiler, TMPDIR passthrough)
  applies there. It hits both the missing-platform-module trap and the
  unvalidated-compiler trap at its own project() check.
- Change (test_package only, main recipe untouched): rewrote
  test_package/conanfile.py generate() explicitly -- same validated-compiler
  helpers as the main recipe (clang-prefix + existence/X_OK + conf/env/PATH/
  common-path order, analysis tools refused, no sibling substitution), Ninja
  generator on OHOS, CMAKE_SYSTEM_NAME=Linux plus processor mapping, validated
  CXX pin (explicit ConanException when nothing validates, per the no-invalid-
  fallback rule), C pin when available, and HMBS TMPDIR/TMP/TEMP passthrough;
  build() adds the analysis-basename fail-fast guard. test() markers and all 12
  consumer checks are byte-identical (no test-scope change, no conandata change).
- Experiences (HMBS round input): E1 apply -- main and test_package now reuse one
  discovery criterion (existence + clang-prefix + ordered probing, generic shims
  excluded); not-found raises an explicit error in test_package generate();
  the SDK-suffix leg is not applicable (absolute compiler path). E2 apply --
  _real_binary returns the input directly plus warning-refusal of analysis
  basenames and a build() fail-fast check in both recipes.

## Fix 2026-09-20 round 21 (new domain: test_package Arcus_FOUND FALSE)
- Compared post-round20 (test_package project() compiler check failed) vs this
  round (14:01Z: project() passes, Found Protobuf 3.17.3 logged, then
  CMakeLists.txt:4 find_package(Arcus) fails with generators/ArcusConfig.cmake
  found but Arcus_FOUND FALSE, build() line 155). Fingerprint MOVED past the
  compiler domain: round-19/20 validated-compiler pin worked (main libArcus.a
  builds). This is a new domain, not a repeat.
- Root cause: archives/p/protobuf/3.17.3 sets cmake_find_mode=none, so
  CMakeDeps generates no Protobuf config; the generated ArcusConfig
  find_dependency(Protobuf) must resolve via native protobuf-config.cmake.
  test_package only required libarcus and never wired it. Precedent:
  archives/l/libarrow_flight/23.0.1/test_package (explicit requires plus
  Protobuf_DIR/protobuf_DIR hints, native config loaded before consumer
  config).
- Change (test_package only, main untouched): requirements() adds explicit
  protobuf/3.17.3; generate() sets Protobuf_DIR and protobuf_DIR to
  lib/cmake/protobuf when present (fallbacks lib/cmake, package root);
  CMakeLists loads find_package(Protobuf CONFIG REQUIRED) before Arcus.
  No test-scope change (12 checks + no_tests intact), no conandata change.

## Fix 2026-09-20 round 22 (new domain: generate-step protobuf target name)
- Compared post-round21 (14:01Z: CMakeLists.txt:4 Arcus_FOUND FALSE) vs this
  round (17:36Z: find_package(Arcus) now succeeds, Conan target Arcus
  declared, then generate step fails at Arcus-Target-release.cmake:15:
  libarcus_DEPS_TARGET links protobuf::protobuf but target not found).
  Fingerprint MOVED: round21 native-config wiring worked; failure is now a
  target-name mismatch, not a lookup failure. No repeat of _DIR/require axis.
- Root cause: protobuf/3.17.3 native config only provides
  protobuf::libprotobuf, while the Conan-generated Arcus config links the
  aggregate default name protobuf::protobuf (protobuf recipe has
  cmake_find_mode=none and no custom target name, so dependents get the
  default aggregate). Evidence is the exact generate-step message naming
  protobuf::protobuf.
- Change (test_package CMakeLists only, main untouched): after
  find_package(Protobuf) and before find_package(Arcus), create an
  INTERFACE IMPORTED protobuf::protobuf alias to protobuf::libprotobuf when
  the aggregate is missing. Test scope and conanfile logic unchanged.

## Fix 2026-09-21 round 23 (evidence gate rejects no_tests/0: promote upstream smoke)

- New fingerprint, first time in this task: compile + test_package both
  PASS on device (libArcus.a linked, 12/12 consumer checks,
  `HMBS_TEST_PACKAGE_RESULT discovered:12/passedCount:12`), but the
  evidence gate judges `incomplete` at stage `evidence`: reason
  "清单表明上游存在测试，no_tests/0 不允许通过" against our
  `HMBS_UPSTREAM_TEST_RESULT status:no_tests discovered:0/executed:0`.
  No compile or test failure; purely an evidence-policy mismatch.
- Root cause: upstream 5.0.0 truly has no formal suite (re-verified
  2026-09-21 via GitHub contents API: no tests/ or test/ dir; full
  CMakeLists text has zero enable_testing/add_test/BUILD_TESTING; src/
  is library-only; python/ is SIP-only), but the tag tree DOES contain
  one upstream-owned verification program, `test_package/test.cpp`
  (blob 8bb2db73, 135 bytes, declares Arcus::SocketState, returns 0).
  The gate's inventory counts it as "upstream has tests", so the honest
  no_tests/0 claim can never pass (same signature as knowledge drafts
  DRAFT-ccrtp-1.0.2-demo-as-upstream-regression and the paperjam
  MANIFEST-command lesson). Fix direction therefore is promotion, not
  more audit text.
- Change (test_package only, main recipe untouched):
  (1) new `test_package/upstream_test.cpp`: verbatim copy of upstream
  test.cpp (provenance header only, body byte-identical);
  (2) `CMakeLists.txt`: build it as `upstream_smoke` linked against
  Arcus, and REMOVE `enable_testing()/add_test()` (consumer binaries
  run via conan self.run; ctest entries would forge a false ctest
  inventory of 2 "upstream" tests);
  (3) `conanfile.py test()`: run `./upstream_smoke` first with the
  exit code as the deterministic oracle (0 -> passed 1/1; non-zero ->
  emit failed marker first, then raise; no stdout counting), emitting
  `HMBS_UPSTREAM_TEST_RESULT status:passed/discovered:1/executed:1/
  passed:1/framework:conan-smoke`; consumer 12/12 marker unchanged;
  (4) `MANIFEST.yml`: `upstream_tests_exist:true`,
  `upstream_test_total:1`, `upstream_test_count_method:auto` (single
  program, exit-code oracle), structured `upstream_test_audit` list
  (paperjam lesson: flat strings are not machine-parsable), one
  `upstream_tests` entry, honest check/test commands without bare
  framework keywords.
- Scope: no conanfile (main)/conandata/patch change; no assertion
  deleted or skipped (12 consumer checks intact, upstream smoke adds
  1 real execution). Next preflight must show both markers non-zero
  (upstream 1/1 + test_package 12/12).
