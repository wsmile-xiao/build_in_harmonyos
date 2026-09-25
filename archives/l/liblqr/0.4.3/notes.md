# liblqr 0.4.3 OpenHarmony adaptation

## Source

The source archive is the GitHub auto-generated tag archive
`https://github.com/carlobaldassi/liblqr/archive/refs/tags/v0.4.3.tar.gz`.
Note: the project has **no release asset** for v0.4.3 —
`releases/download/v0.4.3/liblqr-0.4.3.tar.gz` returns 404; the tag archive
is the only verified download URL (sha256 re-checked by direct download).

## Adaptation

- Accept the `aarch64-linux-ohos` Autoconf triplet in the bundled
  `config.guess`/`config.sub` (0001/0002).
- Relax the hard-coded `umask 077` inside `configure` to `umask 022` (0003): with HMDFS
  setgid build directories (drwxrws--x) it turns mktemp directories into
  drwx--S---, which the build user cannot enter (E114 pattern, previously
  seen in aaphoto 0.45).
- glib dependency resolved via Conan `glib/2.88.3` and consumed through
  pkg-config, matching upstream's own `lqr-1.pc` (`Requires: glib-2.0`).
- Man pages are not installed (`--enable-install-man` off): the man
  subdirectory only builds conditionally and 88 man pages add no value to
  the SDK package.
- Shared build is the default (`AC_DISABLE_STATIC` upstream); the recipe
  keeps both `shared=True/False` options and both variants were verified.

## Verification

- `make check`: completed successfully; upstream ships no test cases
  (top-level `SUBDIRS = lqr man`, no `TESTS`), so the target is an
  automake no-op pass — executed for real to prove it, not assumed.
- `test_package/test_lqr_package`: 7/7 assertions passed on the
  HarmonyOS PC device (seam carve 8x4 -> 6x4, pixel scan invariants).
- OHOS-specific checks (shared package): ELF64/AArch64 header, NEEDED
  `libglib-2.0.so.0` + `libc.so`, SONAME `liblqr-1.so.0`, no leaked
  RPATH/RUNPATH, test binary resolves the packaged .so at runtime.
- static variant: direct link against `liblqr-1.a` + run, ELF checks
  skipped (no .so in package) — both package variants green.
