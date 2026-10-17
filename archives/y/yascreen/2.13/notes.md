# yascreen 2.13 adaptation notes

## Scope

- Platform task: 12267（开源鸿蒙PC专项积分赛-依赖）
- Branch: `feat/yascreen-2.13`
- Package: `yascreen/2.13`
- Worktree: `~/qzy/DS-4-yascreen-2.13`（upstream/main = 4cf129ecfc）

## W0 dependency check

`ci/scripts/preflight_check.sh yascreen/2.13` reports no dependency declarations
(required list empty); the library links only libc. Nothing to verify against
the artifact registry, nothing to split out. Re-checked after the recipe was
written: `conanfile.py` declares no `requires()`.

## W0b history / language preflight

- No prior `archives/y/yascreen` adaptation exists upstream, so there are no
  historical notes to migrate.
- Language: upstream is pure C (yascreen.c / yascreen_feed.c / yastest.c);
  the task language (C/C++ family) matches; no `env_unsupported` path applies.

## Source and build analysis

- Official source: `https://codeload.github.com/bbonev/yascreen/tar.gz/refs/tags/v2.13`
  (filename pinned because codeload URLs have no suffix; Conan would otherwise
  pick ZIP extraction)
- SHA-256: `cfcb74ee8b3b5ff2d367221d3f997f538416ee9bf2056d8f1c29d88eeab5b38f`
- License: LGPL-3.0-or-later.
- Upstream ships a `Makefile` wrapper that re-executes itself through `gmake`
  (`@if [ ! -x "$(command -v gmake)" ] ...`), which does not exist on the
  target. The recipe drives `GNUmakefile` directly and needs no patch for this.
- `Makefile.main` hardcodes `AR=gcc-ar` / `RANLIB=gcc-ranlib` (GNU LTO
  tooling). The clang toolchain has no `gcc-ar`, so the recipe overrides them
  on the make command line with `llvm-ar` / `llvm-ranlib`; command-line
  variables take precedence over makefile assignments.
- Upstream warning flags are self-probing (`check_cc_flag` compiles a probe
  for `-flto=auto` etc. and drops unsupported flags), so no flag surgery is
  needed for clang.
- The `install` target depends on `yascreen.3`, generated from `README.md` by
  `go-md2man` (a Go tool, unavailable and unnecessary). The recipe therefore
  does not call `make install`; `package()` copies `libyascreen.a`,
  `libyascreen.so.0.0.0`, `yascreen.h` and the generated `yascreen.pc`
  directly.
- The shared library is built with `-Wl,--version-script,yascreen.vers`
  (`SONAME libyascreen.so.0`). Because the upstream build always produces both
  static and shared artifacts, `package()` ships only the artifact selected by
  the `shared` option: keeping both in `lib/` makes the linker pick the `.so`
  even for static consumers, and musl ignores DT_RUNPATH so the test binary
  then cannot load the versioned soname at runtime (observed in the first
  conan-verify run, fixed by option-scoped packaging).
- No patches are required (`patches/` is empty); `apply_conandata_patches()`
  is still called explicitly per the recipe validator convention.

## Upstream test inventory (五维账本)

- `N_static` = 0. Evidence: `GNUmakefile` defines no `check`/`test` target and
  `all` builds only `libyascreen.a libyascreen.so yascreen.pc`; the GitHub
  Actions workflow (`.github/workflows/c-cpp.yml`) runs plain `make` (build
  only) across Linux/macOS/FreeBSD/OpenBSD matrices.
- `yastest.c` is an interactive visual demo (drives a real terminal with
  `sleep()` calls, all assertion-like checks are commented out in `#if 0`
  blocks or print-only). It is not registered in any test runner and cannot
  assert behaviour in an automated run; counted as 0 executed with the
  technical reason "upstream ships no automated suite".
- `N_registered` = 0, `N_executed` = 0 (upstream), `N_consumer` = 1 (below).
- Per the workspace rule "上游无自动化测试时如实写 0，再设计真实 API/行为测试",
  the consumer test carries the verification burden.

## Consumer test

`test_package/test.c` links the installed `yascreen::yascreen` target and
exercises the public API headlessly (no TTY required) by installing an output
callback through `yascreen_setout()`:

1. `yascreen_init(20,10)` returns non-NULL
2. `yascreen_sx`/`yascreen_sy` report 20/10
3. `yascreen_setout` accepts the capture callback (returns 0)
4. `yascreen_putsxy` writes "hello" without error
5. `yascreen_update` flushes and the captured buffer contains the text
6. `yascreen_resize(30,12)` returns 0 and the geometry getters report 30/12
7. `yascreen_clear` + `yascreen_free` complete without crashing

`assertion_count: 7` in `test_package/MANIFEST.yml`.

## Path B judgment

Judged **not** path B. The adaptation uses the standard raw-makefile recipe
pattern already covered by existing recipes and workspace experience
(makefile template + command-line tool overrides); the only notable finding
(static+shared co-packaging making the linker prefer `.so` under musl's
RUNPATH behaviour) is a workspace-level known pattern, not new cross-repository
knowledge produced by this task. No knowledge draft is attached to this PR.

## True-device validation

`conan-verify yascreen 2.13` (CONAN_HOME `~/tmp/ch/home-DS-4-yascreen`,
profile `ci/conan/profiles/ohos-aarch64`, conan 2.29.1):

- Run 1: G2 failed in the test_package stage with
  `Error loading shared library libyascreen.so.0` / relocation errors —
  the linker had picked the shared artifact for a static default package.
  Fixed by shipping only the option-selected artifact in `package()`.
- Run 2: G1 ✅ G0 ✅ G2 ✅ G3 ✅ G4 ✅ L2 ✅ L4 ✅ L5 ✅; consumer test executed
  natively: `yascreen consumer test: all assertions passed`.
- Report: `reports/conan-verify-report.md` (run 2); logs kept under
  `~/tmp/uc2/DS-4/yascreen/`.

## CI note

Workspace instruction for this window: do **not** post `/rebuild`. CI
triggering for this PR is deferred until the platform recovers (user-arranged
follow-up agent). Everything up to and including PR creation is complete at
this HEAD.

## 最终状态

- 状态：`built`（conan-verify 全门禁通过，消费者测试 7/7 断言通过）
- 下一步：平台恢复后由跟进 agent 触发 CI（`/rebuild`）→ `/ai review` →
  意见闭环 → 四件套复核 → `$P request-review <PR>` 提审
- 证据：本文件 + `reports/conan-verify-report.md` + result.json 草稿
  （milestone=w3_finish_started，PR 创建后升级为带 pr_url 的 partial）
---

**编译结束**: 2026-09-20 16:41
**最终状态**: built
