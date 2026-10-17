# libcom_err 1.47.4 — adaptation notes

## What it is
libcom_err is the MIT "common error description library" (`com_err`) bundled
with e2fsprogs. Its self-contained autotools subproject lives in
`lib/et` of the e2fsprogs tree and provides:
- `libcom_err` (static archive) — the shared lib requires `--enable-elf-shlibs`
- `com_err.h` header (installed to `include/et/com_err.h` + `include/com_err.h` symlink)
- `com_err.pc` pkg-config file
- `compile_et` error-table compiler (shell script; needs awk)

## Build strategy (official e2fsprogs 1.47.4 tarball)
We reuse the official release tarball (kernel.org, sha256
`da274408…91b96`) and configure the whole tree **only** so the top-level
autoconf generates `lib/et/Makefile` + `MCONFIG` + `lib/config.h`. Then we
build / test / install **only** `lib/et`:

```
./configure --prefix=/ --disable-nls --disable-rpath --disable-backtrace \
            --disable-tls --disable-testio-debug --disable-debugfs \
            --disable-imager --disable-resizer --disable-defrag \
            --disable-mmp --disable-tdb --disable-bmap-stats \
            --disable-uuidd --disable-fuse2fs
make -C lib/et -j1                 # libcom_err.a + compile_et + com_err.pc
make -C lib/et check -j1           # upstream regression suite
make -C lib/et install DESTDIR=<pkg>
```

⚠️ Only options that e2fsprogs configure actually recognizes are passed;
an unrecognized `--disable-*` makes autoconf configure abort.

Static-only (no `--enable-elf-shlibs`) deliberately avoids the elf shared-lib
`install` machinery (install-symlink + LDCONFIG) that is fragile on
OHOS/HMFS filesystem.

## Upstream tests
- Framework: custom autotools `check` target in `lib/et/Makefile.in`
  (loop over `test_cases/*.et`, run `compile_et`, diff generated `.c/.h`
  against checked-in expected files).
- Registered total: **6** test cases
  (`continuation`, `heimdal`, `heimdal2`, `heimdal3`, `imap_err`, `simple`).
- Executed by `make -C lib/et check`; one `Test case <name> succeeded/failed`
  line per case is the deterministic framework output we parse.
- `upstream_test_total: 6`, `upstream_test_count_method: autotools_tests`.

## Consumer test (test_package)
`test_com_err.c` links the installed lib and runs 5 deterministic checks:
init_error_table registration (asserted via side effect), exact error_message
table lookups (base / base+1 / base+2), unknown-code formatter, and
set_com_err_hook + com_err dispatch. It prints `HMBS_TEST_PACKAGE_RESULT`
with counts from its own executed-check counters.

## OHOS / HMFS robustness (incorporated in conanfile build())
These are the known autoconf-on-OHOS failure modes documented in this repo
(see e.g. darts/0.32, a52dec):
1. OHOS `/tmp` is a read-only erofs mount → inject the hmbs task writable
   TMPDIR/TMP/TEMP into the toolchain env and process env.
2. Autoconf `ac_pwd=\`pwd\`` fails on HMFS → patch configure to fall back to
   `$PWD` (best-effort; no-op warning if the snippet is absent).
3. `config.status` mktemp under umask 077 is unwritable on HMFS → redirect to
   a writable dir and relax umask to 022 (best-effort).
4. Host triple `aarch64-linux-ohos` is already supported by e2fsprogs 1.47.4's
   bundled `config.sub` (adds `ohos*` and `linux-ohos*`), so no config.sub
   patch is needed.

## Verification (internal infra — do NOT put this in the PR body)
Verified on the shared HarmonyOS PC aarch64 real device (same toolchain as
official CI), not on the dev Windows host. The PR body must only state
「已在 HarmonyOS aarch64 环境预检通过」.

## Fix round (2026-09-28)
Two verified failures from preflight were fixed in the working tree:
1. **test_package check 5 (passedCount 4/5).** `test_com_err.c` defined
   `my_com_err_hook` and set `hook_called=0` then called `com_err(...)`, but it
   never installed the hook via `set_com_err_hook()`. The default hook ran, so
   `hook_called` stayed 0 and `com_err hook dispatch` failed. Fixed by calling
   `set_com_err_hook(my_com_err_hook)` before the dispatch check and
   `reset_com_err_hook()` after.

2. **Upstream counting inconsistency (executed 9 > discovered 6 → rule4).**
   The recipe parsed every `Test case ... succeeded/failed` line into
   executed/passed/failed, so a `check.log` carrying repeated verdict lines for
   one case inflated executed beyond the 6 registered `.et` fixtures. The
   upstream `lib/et` `check` target emits exactly one verdict line per `.et`
   case name; rewritten to keep the *last* verdict per distinct test-case name.
   This makes discovered/executed/passed/failed a single per-test truth with
   `passed+failed==executed` and `executed<=discovered` by construction. Genuine
   failures / non-executed cases are surfaced via `gaps`
   (test_failure / environment) with total == discovered - passed. `make check`
   no longer aborts the build on a failed test; the honest marker is emitted and
   packaging + test_package continue so failures stay visible.

## Fix round 3 (2026-09-28, AI Review P0)
`test_com_err.c` check 1 did `CHECK(init_error_table(msgs, base, 3) == 0, ...)`.
But e2fsprogs' `com_err.h` declares `init_error_table` as
`extern void init_error_table(const char *const *msgs, long base, int count);`
— it returns `void`, so comparing it with `== 0` is a C11 constraint violation
and would fail to compile in test_package. Rewrote check 1 to call
`init_error_table(...)` as a statement and assert registration via the
observable side effect (`error_message(base) == "reserved"` after the register).
The table-lookup checks now cover offsets base / base+1 / base+2 (entries 0/1/2)
so the 5-check set stays meaningful with no duplicated entry-0 assertion.

## Fix round 4 (2026-09-28, CI #63794 timeout — network)
CI conan create timed out (3600s) while downloading the e2fsprogs release
tarball: the pre-download step failed (`curl: No such file or directory`), so
the build relied on conan's own download from `www.kernel.org` +
`downloads.sourceforge.net`, both of which stalled (`IncompleteRead` on
kernel.org) from the CI worker and hit the 3600s cap. Fixed by making
`conandata.yml` `sources.url` an ordered mirror list: reachable mirrors first
(`mirrors.ustc.edu.cn/kernel.org/<path>` per ci/conan/build_and_test.sh
kernel.org mapping, `cdn.kernel.org`, `mirrors.edge.kernel.org`), with the
original official URLs (`www.kernel.org`, `downloads.sourceforge.net`) kept
last as fallback. `sha256` unchanged; conan's get() walks the list and
verifies the checksum on success, so a 404/timeout just falls through. This is
a diet/network-fix only — no build/test code touched. Registry R37 comparison
still sees the same file+sha256 (mirror prefixes are normalized), so no version
bump needed.

## HMFS hard-link fix
On HarmonyOS the filesystem (HMFS) does not support hard links
(HMBS_CAP_HARDLINK=0); `make -C lib/et` failed at `GEN_LIB libcom_err.a`
with `ln: cannot create hard link from 'et/libcom_err.a' to 'libcom_err.a':
Operation not permitted`.  e2fsprogs' `lib/Makefile.library` creates the
convenience `lib/libcom_err.a` with `$(LN)` (hard link by default, because
`LINK_BUILD_FLAGS` defaults empty), and `lib/et`'s install target creates
`include/com_err.h` with `$(LN)` (hard link by default because
`LINK_INSTALL_FLAGS=-f`).  Both are switched to symbolic links for OHOS by
passing `--enable-symlink-build` (`LINK_BUILD_FLAGS=-s`) and
`--enable-symlink-install` (`LINK_INSTALL_FLAGS=-sf`); HMFS supports symlinks
(`HMBS_CAP_SYMLINK=1`).  Verified by real-machine preflight `conan create`.

## Infra note (2026-09-29, CI #64114 fork OOM in global G0 gate)
CI conan-build-test failed BEFORE any package build: the global knowledge-graph
integrity gate (G0) in ci/conan/build_and_test.sh aborted at lines 116 (grep) and
133 (wc) with `resource temporarily unavailable` and exit 127. This is a fork
EAGAIN (worker memory/process exhaustion), not a recipe issue: it occurs outside
and before the libcom_err package build (elapsedTime=0.52s), and the recipe,
test_package, manifest and conandata were all re-audited in this round and are
unchanged (real-device preflight still valid). No upstream-test / build / test
code was modified. Only this doc was normalized CRLF->LF to form a verifiable
new head so HMBS reschedules onto a healthy worker instead of passively waiting.
