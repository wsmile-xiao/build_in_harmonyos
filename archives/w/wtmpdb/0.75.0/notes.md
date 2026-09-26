# wtmpdb 0.75.0 adaptation notes

- Upstream is Meson + C, a sqlite3-backed replacement of wtmp/lastlog with a
  PAM module; it never calls utmpx APIs itself (probe: `utmpx` hits 0 in the
  sources), so the OHOS utmpx gap (E121) does not apply — wtmpdb is the
  replacement implementation, not a consumer.
- **libpam gap + rescue**: OHOS sysroot and harmonybrew contain no libpam;
  `cc.find_library('pam')` (meson.build:94, required) fails configure with
  `C shared or static library 'pam' not found`. The registry already
  publishes linux-pam/1.7.2 (libpam.so.0, include/security/*.h, module dir),
  so the recipe depends on it. Wiring meson to conan deps needed three
  pieces (the "tripod", see DRAFT-wtmpdb-0.75.0-ohos-libpam-rescue-meson-tripod):
  1. `Environment(scope=build)` prepends dependency `lib/` into LIBRARY_PATH
     and LD_LIBRARY_PATH and `include/` into CPATH — meson find_library does
     not consume pkg-config files;
  2. `-Dsplit-usr=true` aligns upstream's distro rootprefix self-check with
     conan's `prefix=/` + DESTDIR install (pam module lands in
     package_folder/lib/security);
  3. plocate-style native `[binaries]` pinning (ar/ranlib/strip/pkgconfig
     absolute paths from profile conf) — conan's build PATH lacks the
     toolchain dir.
- audit/libsystemd/wtmpdbd are feature:auto and disabled here (no systemd on
  OHOS): delivered surface = libwtmpdb.so + wtmpdb CLI + pam_wtmpdb.so,
  **without the wtmpdbd daemon** (disclosed as a known limitation).
- Upstream tests executed for real inside build() via meson.test():
  6 registered = 4 Ok + 2 upstream self-skips (exit 77 by upstream's own
  guards): tst-get_id gets SQLITE_CANTOPEN(-14) because /var/lib/wtmpdb is
  not creatable for a non-root user; tst-varlink returns early when
  getuid()!=0 (and wtmpdbd is disabled anyway). tst-dlopen printed
  `dlopen() of "./pam_wtmpdb.so" succeeded` — the runtime proof that the
  PAM module builds and loads on OHOS.
- test_package consumer (6 assertions) links libwtmpdb and calls only the
  version-script-exported API (wtmpdb_login/logout/read_all/get_id) against
  a temporary sqlite db on HMDFS; discovered semantics: get_id returns -2
  with "Open entry ... not found" for closed sessions (initial assertion
  used -1 and was corrected against the real device reading, not the docs).
- sqlite3 on HMDFS works end to end (create/insert/reopen persistence, file
  mode 640 under the worker umask; the case-insensitive filesystem is not an
  issue for the all-lowercase default /var/lib/wtmpdb/wtmp.db path).
- No source patches were needed (patches_applied is empty).
- **CI-only failure fixed (PR #12392, hw-6 2026-09-24)**: CI failed at `conan-build-test` with
  `../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]` while every local run was green.
  Root cause = profile asymmetry (经验汇总 §12.90): the shared CI profile's
  `tools.build:compiler_executables` carries only `c`/`cpp`, so `_inject_binaries()` got
  `executables.get("ar") -> None` and hit a silent `continue` -> no `ar` in `[binaries]` ->
  meson probed the bare name `llvm-ar`, which the CI worker PATH cannot resolve. The window
  profile written by `hw-win-setup.sh` does carry `ar`/`ranlib`/`strip`, which is why this
  recipe never failed on device. Fix: resolve `ar`/`ranlib` in three layers (profile key ->
  alongside the profile compiler -> `shutil.which`), and raise instead of skipping silently.
  `strip` deliberately stays conf-only: the OHOS clang wrapper signs the ELF at link time, so
  a meson-side install strip would invalidate that signature.
  Shadow-CI A/B on device (`~/tmp/uc2/hw-6/cishape.log`; PATH with no ar-family name, conf with
  c/cpp only): HEAD recipe -> rc=1, verbatim `ERROR: Unknown linker(s): [['llvm-ar-15'],
  ['llvm-ar'], ['ar'], ['gar']]`, `[binaries]` = pkgconfig/c/cpp only; patched recipe -> rc=0
  (`conan create` + `meson.test()` + test_package), `[binaries]` gains
  `ar = '/storage/Users/currentUser/usr/local/bin/llvm-ar'` and `ranlib = ...`.
  Local gates re-run after the fix: `ohc-run.py conan-verify wtmpdb 0.75.0` G0-G4 PASS
  (`~/tmp/uc2/hw-6/wtmpdb-verify2.log`).
---

**编译结束**: 2026-09-24 17:35
**最终状态**: built
