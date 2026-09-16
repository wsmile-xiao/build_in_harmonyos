# gcc-ada 9.5.0 HarmonyOS adaptation notes

Issue: #2281

## Current state

The native OHOS/AArch64 GCC 9.5 Ada compiler, target libgcc, libgnat,
libgnarl, GNAT tools, package installation, and consumer execution have all
passed targeted real-device validation. The final package test passed on
2026-08-22 and covered strings, containers, exceptions, protected objects,
and tasking; see `reports/device-validation-r144.md`.

Clean CI #36815 passed on 2026-09-02 from commit `07ec8b19a7`, including the
complete source build, package installation, consumer test, DejaGNU driver,
the 41-case installed-package subset, L0 and L1. A later C-candidate follow-up
ran the complete build-tree GNAT/ACATS suites in CI #42755 from commit
`894036c82bc`, producing the one-off full-suite evidence for the 3542 upstream
results. The installed-package subset remains tracked separately as 41/41 so
reviewers can distinguish post-install executable coverage from the full
build-tree testsuite result.

The review follow-up added complete build-tree GNAT and ACATS validation with
a temporary signed native proxy for `gcc/xgcc`. CI #42755 captured that
full-suite evidence successfully. CI #42817 then showed that rerunning the
same complete suites on every merge-gate rebuild can exceed the default 3600
second `conan create` window while inside ACATS. The PR therefore keeps the
full-suite path available as an explicit evidence rerun with
`GCC_ADA_FULL_UPSTREAM_TESTS=1`, while the default CI path builds the package
and reruns the 41-case installed-package upstream subset plus consumer checks.

The selected upstream inputs are not duplicated in `test_package`. During
`package()`, the recipe copies the 46 checksum-verified GCC GNAT/ACATS source
inputs needed by the 41 executable cases into
`share/gcc-ada/upstream-tests`. The consumer test resolves that directory from
the installed dependency package; the package-owned DejaGNU driver remains in
`test_package`. This keeps the test source provenance and execution contract
while reducing review noise from verbatim upstream copies.

The latest review inventory counts `N=4315` upstream test entries. The recorded
execution count is `N'=3542`, with `3542/3542 (100%)` passing among the
executed result records. The remaining `773` inventory entries have no
independent result record in CI `#42755`; they are not claimed as executed or
passed. The report keeps the inventory and execution counts separate, and the
primary evidence denominator remains `3562 = 3542 + 20`.

The first full-suite CI attempt (#38711) reached `check-gnat` and executed its
parallel shards, but GCC's `dg-extract-results.sh` could not write into a
mode-0700 child below the HMDFS-backed Conan build `.tmp` directory. The
recipe now places `TMPDIR` on the app-local XPM filesystem already used by the
bootstrap and emits bounded, de-duplicated failure evidence from upstream log
files when a suite reports unexpected results.

CI #40540 then reached the ACATS support-generation phase and failed before
the suite could produce a full result set because `macrosub.adb` was not
generated. GCC 9.5's `run_acats.sh` captures the host-side `gnatchop` before
running the target suite; the recipe now validates and wraps the Alpine seed
`gnatchop` through the same XPM loader path as `gnatmake`, `gnatbind`, and
`gnatlink`, so the host ACATS preprocessors can be chopped without attempting
to execute a bare Alpine ELF on OHOS.

CI #40598 then moved past that support-generation step and failed while
linking `macrosub` itself: the seed linker could not resolve musl-side symbols
from `libgnat-9.so` because the launcher only carried runtime library search
paths. The seed launcher now also exports `LIBRARY_PATH` alongside
`LD_LIBRARY_PATH`, so seed `gnatmake`/`gnatlink` can find the musl libc and Ada
runtime at link time as well as at execution time.

CI #40665 did not reproduce that link failure; instead it timed out on a slow
worker before reaching libada or the upstream suites. The recipe keeps the same
bounded build strategy but raises the package-local parallel cap from four to
eight jobs, then avoids repeated signing work so the full compiler build and
default installed-package tests fit the merge-gate CI window without changing
repository CI timeout infrastructure.

CI #40703 showed that GCC's driver-level `LIBRARY_PATH` alone does not resolve
`libgnat-9.so`'s transitive `DT_NEEDED` entry for
`libc.musl-aarch64.so.1` when the seed driver delegates to the OHOS linker.
The seed GCC wrapper now also passes explicit `-Wl,-rpath-link,...` entries for
the bootstrap runtime, seed musl library directories, GCC seed library
directory, and Ada `adalib` directory.

The explicit full-suite path still includes the earlier fixes from #38711
through #40759: DejaGNU temporary files use the app-local XPM filesystem,
Alpine seed `gnatchop` is wrapped through the XPM loader, seed links receive
`LIBRARY_PATH` plus explicit `-Wl,-rpath-link,...` entries, and the bootstrap
library directory exposes both `ld-musl-aarch64.so.1` and
`libc.musl-aarch64.so.1`.

## Bootstrap decision

GCC's Ada frontend is written in Ada, so every source build needs an existing
GNAT. The recipe uses Alpine Linux 3.12's official AArch64/musl GCC/GNAT 9.3
packages as a checksum-pinned, build-only seed:

- the seed is older than the GCC 9.5 target, matching GCC's bootstrap advice;
- its ELF interpreter is `/lib/ld-musl-aarch64.so.1`, matching the OHOS musl
  execution model;
- `gnat`, `gnatmake`, `gnatbind`, `gnatlink`, and `gcc` need only musl;
- `gnat1` additionally needs `libisl.so.15`, `libmpc.so.3`, `libmpfr.so.6`,
  `libgmp.so.10`, and `libz.so.1`, all pinned from the same Alpine repository;
- the recipe signs copied seed ELF files before first execution and discards
  the complete seed after the source build.

This follows the repository's established compiler pattern: a trusted binary
toolchain is a verified source input to `conan create`, not an undeclared PATH
dependency and not a runtime component of the output package.

## Build flow

1. Download official GCC 9.5.0 plus GCC-selected GMP/MPFR/MPC sources.
2. Apply package-owned OHOS triplet, musl, sysroot, HMDFS, generator, pthread,
   and Ada runtime transforms.
3. Download and SHA256-verify nine Alpine seed APKs, safely extract their gzip
   member chains, materialize required links, and verify the GNAT layout.
4. Copy and sign the seed, then compile an Ada unit with seed `gnatmake -c`.
5. Configure native `aarch64-linux-ohos` GCC with C and Ada enabled.
6. Build/sign `all-gcc`, target libgcc, PIC target libada, and the six native
   GNAT tools used by the package and upstream suites (`gnatbind`, `gnatmake`,
   `gnatlink`, `gnatchop`, `gnatls`, and `gnatclean`) in explicit phases, then
   run the GCC selftest.
7. By default, leave the expensive build-tree GNAT/ACATS suites out of the
   merge-gate rebuild because CI #42755 already captured the 3542-result
   full-suite evidence and CI #42817 proved repeated full-suite runs exceed
   the default window. Set `GCC_ADA_FULL_UPSTREAM_TESTS=1` to rerun complete
   upstream `check-gnat` and `check-acats` explicitly.
8. Install GCC/GNAT tools, `gnat1`, libgcc, libgnat/libgnarl, Ada sources and
   ALI files; package `gcc` as a signed relocatable native proxy and copy the
   46 selected upstream GNAT/ACATS source inputs under
   `share/gcc-ada/upstream-tests`.
9. The package driver supplies the OHOS SDK sysroot and static SDK
   `libunwind.a` for links. `test_package` compiles, binds, links, signs, and
    executes its Ada consumer plus a 41-case upstream GNAT/ACATS subset from
    the installed package's test-source directory.

## Resolved device findings

- The signed XPM loader plus short NEEDED names allows the Alpine GNAT seed to
  compile `seed_probe.o` (`SHORT_NEEDED_DIAGNOSTIC=pass`).
- OHOS lacks `pthread_cancel`, `pthread_mutexattr_setprioceiling`, and
  `pthread_rwlockattr_setkind_np`; package-owned source transforms avoid those
  Linux-only runtime calls.
- Target runtime C objects require `-fPIC`; this removes the invalid static
  `environ` relocation seen during the first package link.
- GCC 9's native `unwind-dw2` hangs while raising an Ada exception on this
  platform. The SDK AArch64 `libunwind.a` passed the r143 A/B diagnostic and
  is injected only for link invocations by the installed driver wrapper.
- HarmonyOS cannot directly execute package shell drivers. Signed native
  proxies resolve adjacent hidden wrappers through `/proc/self/exe`.

## Resume commands

```sh
python3 scripts/ohc-run.py conan-verify gcc-ada 9.5.0
CI_PACKAGES="archives/g/gcc-ada/9.5.0" zsh ci/conan/build_and_test.sh
```

Run the second command only while holding the global device lock. Clean CI
#36815 passed the installed-package subset, and CI #42755 passed the complete
build-tree GNAT/ACATS evidence run. The default merge-gate CI now reruns the
package build plus the 41-case installed-package upstream subset; use
`GCC_ADA_FULL_UPSTREAM_TESTS=1` only when a dedicated full-suite evidence rerun
is needed.

## Command registration

The approved software-level `archives/g/gcc-ada/commands.json` registers the
four required package executables: `gcc`, `gnatmake`, `gnatbind`, and
`gnatlink`. The only additional files outside the gcc-ada archive are the
paired knowledge drafts under `knowledge/drafts/`, as required by the Wiki;
no framework or unrelated archive files are included.

### 对话 #2281 / PR #6116

- 2026-09-09: 对照仓库 Wiki 补齐软件级归档文件、版本测试计数和标准测试报告。
- 2026-09-09: 最新轻量门禁 CI #42923 通过；完整 3542 项上游证据继续引用 CI #42755。
- 2026-09-10: 将 46 个未修改上游 GNAT/ACATS 测试源改为随已安装包提供，
  `test_package` 从 `share/gcc-ada/upstream-tests` 读取，保留 41/41 执行覆盖。
- 2026-09-11: 按最新审查统计补充上游入口清单 `N=4315`，并明确实际运行
  `N'=3542`、运行通过率 `3542/3542`；清单差额 773 项没有独立结果记录，
  不计为已执行或 PASS。

## 最终状态

- status: built
- Latest merge-gate: CI #42923 passed on `ohos-aarch64` with Conan
  `test_package`, L0, L1, and cleanup all green.
- Upstream inventory: latest review count `N=4315`; CI #42755 recorded
  `N'=3542` executed results with `3542/3542` passing. The remaining 773
  inventory entries have no independent result record and are not claimed as
  passed. The default merge gate keeps the 41-case installed-package subset
  and 20 consumer assertions.
- No release tarball is committed here. This source PR follows the repository
  rule that package archives are produced by the release pipeline, not checked
  into the source archive.
