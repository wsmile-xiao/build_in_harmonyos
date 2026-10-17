# wiggle 1.3 adaptation notes

## Scope

- Platform task: 11893（开源鸿蒙PC专项积分赛-依赖）
- Branch: `feat/wiggle-1.3`
- Package: `wiggle/1.3`
- Worktree: `~/qzy/DS-4-wiggle-1.3`（upstream/main = 4cf129ecfc）

## W0 dependency check

wiggle links ncurses (`LDLIBS = -lncurses`, `#include <curses.h>` in
vpatch.c). The ohpcd registry carries `ncurses/6.5` (binary probe:
`conan install --requires=ncurses/6.5 --build=never` with profile
`ohos-aarch64` downloaded package `21b17f8b2bc0…`, revision `f68a0f13…`) and
`libncurses/6.6_p20260516` (recipe revision `fda64cf8…`). The recipe pins
`ncurses/6.5` — its binary has been published since 2026-08-08 and it ships
the static wide-character library `libncursesw.a` (`cpp_info.libs =
["ncursesw", …]`), so no `libncurses.so` exists to crash the OHOS system
(ncurses GOTCHA). Nothing else to split out: no other `requires()`.

## W0b history / language preflight

- No prior `archives/w/wiggle` adaptation upstream — no historical notes.
- Language: pure C (load/parse/split/extract/diff/bestmatch/merge2/utils.c,
  wiggle.c); task language matches.

## Source and build analysis

- Official source: `https://codeload.github.com/neilbrown/wiggle/tar.gz/refs/tags/v1.3`
  (filename pinned for the codeload suffix)
- SHA-256: `ff92cf0133c1f4dce33563e263cb30e7ddb6f4abdf86d427b1ec1490bec25afa`
- License: GPL-2.0-or-later ("GPL-2+" per `wiggle --version` and COPYING v2).
- `config.h` ships pre-generated; its BYTE_ORDER block resolves against musl's
  `<endian.h>` and selects little-endian on aarch64 — no regeneration needed.
- The build needs no patch file; all deviations are make command-line
  overrides (command-line variables beat makefile assignments):
  - `CWFLAGS` override: keep upstream warning set minus `-Werror` (unsafe with
    a different clang), plus `-I<ncurses include>` (upstream `CFLAGS` has no
    `$(CPPFLAGS)` slot).
  - `LDLIBS="-L<ncurses lib> -lncursesw"`: the ohpcd ncurses package only
    ships the wide static library, and the link line has no `$(LDFLAGS)` slot.
  - `OptDbg=-O2` replaces the default `-ggdb` for a release build.
  - `CC=clang`, `SHELL=<CONFIG_SHELL>` (R33/R5 patterns); `ar` exists on the
    toolchain PATH so upstream's `ar cr` rule is untouched.
- The default `all` target also builds `wiggle.man` via `nroff` (absent from
  the toolchain); the recipe builds the `wiggle` target only. `make install`
  is skipped (`INSTALL=/usr/bin/install`, not used); `package()` copies
  `wiggle` to `bin/`, `COPYING` to `licenses/`, and the preexisting
  `wiggle.1` roff source to `share/man/man1`.
- `wiggle -d` exits with diff(1)-style code 1 when files differ; the consumer
  test asserts on content, not on that exit code (§12.73④ semantics).

## Upstream test inventory (五维账本)

- `N_static` = 71, counted from `dotest`'s registration entries — files named
  `script/diff/ldiff/rediff/merge/wmerge/lmerge/replace/Wmerge/bmerge` under
  `tests/`: by type merge=34, wmerge=9, lmerge=9, diff=8, ldiff=4, Wmerge=3,
  rediff=2, replace=1, bmerge=1; by directory tests/simple=33,
  tests/linux=28, tests/contrib=8, tests/lustre=1, tests/mdadm=1.
- `N_registered` = 71 (all discovered by `dotest` at run time; the Makefile
  wires the suite to the `test` target), `N_executed` = 71, failed = 0.
- Execution: `./dotest` runs inside recipe `build()` and was executed both in
  the exploratory device build and inside `conan create` —
  `71 succeeded and 0 failed`, exit 0. `dotest` writes its valgrind scratch
  log under `/tmp` (read-only on OHOS); the failed redirect is non-fatal and
  valgrind mode is not used — recorded as an upstream-script quirk, not a
  test failure.
- `N_consumer` = 1 program (7 logical assertion groups) in `test_package`.

## Consumer test

`test_package/test.sh` runs the installed binary in a scratch directory:
1. `wiggle --version` output (stderr) reports `wiggle 1.3`
2. `wiggle -m orig patch` merges a 1-hunk patch, output byte-compared (`cmp`)
   against the expected merged file
3. no `<<<<<<<` conflict markers in the merged output
4. `wiggle -dw orig expected` change display contains the added marker
   `<<<++BRAVO++>>>`
5. and the removed marker `<<<--bravo-->>>`
plus the two explicit failure-guard groups around the merge assertions —
7 logical assertion groups total; assertions run against real behaviour, not
print-only.

## Path B judgment

Judged **not** path B. The ncurses wide-character-only packaging pattern
(`-lncurses` → `-lncursesw`) is already covered by existing knowledge entries
(E028 ncurses static-only / E033 wide char) and multiple merged recipes
(aeolus, alpine, …) already link `-lncursesw`; the make-override patterns are
standard workspace practice. 查重命中 → 无新增跨仓库知识，按纯 A 交付。

## True-device validation

`conan-verify wiggle 1.3`（CONAN_HOME `~/tmp/ch/home-DS-4-wiggle`，profile
`ci/conan/profiles/ohos-aarch64`，conan 2.29.1）：

- Run 1: G2 failed in `test_package` — `--version` banner goes to stderr, the
  grep on stdout matched nothing. Fixed with `2>&1`.
- Run 2: G2 failed on the extraction assertion — `wiggle -dw` emits wiggle's
  annotated change display (`<<<++new++>>>`/`<<<--old-->>>`), not a unified
  diff; the anchored `^+BRAVO` grep was wrong. Fixed to assert the markers.
- Run 3: G1 ✅ G2 ✅（含 build() 内 `./dotest` 71/71 + 消费者测试）G3 ✅ G4 ✅
  L2/L4/L5 ✅；`wiggle consumer test: all assertions passed`.
- Logs: `~/tmp/uc2/DS-4/wiggle/logs/`；报告 `reports/conan-verify-report.md`。

## CI note

CI 已于平台恢复后对本 PR 正常触发（`/rebuild`）；CI/AI 结论绑定推送时的
HEAD，闭环由本窗口完成。

## 最终状态

- 状态：`built`（conan-verify 全门禁通过；上游 71/71 + 消费者 7 断言全过）
- 下一步：push → presubmit → CI/AI 闭环 → 四件套复核 → `$P request-review` 提审
- 证据：本文件 + `reports/` + result.json（PR 创建后带 pr_url 的 partial 草稿）
---

**编译结束**: 2026-09-20 17:20
**最终状态**: built
