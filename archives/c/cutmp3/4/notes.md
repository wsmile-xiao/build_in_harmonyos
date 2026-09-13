# cutmp3 4 adaptation notes

## Source and version

The contest task and archive directory use version `4`; the corresponding
upstream release is `v4.0` at commit
`efacd0be328490683c1ac453d13bc6b88f560c33`. The official tag archive and its
SHA-256 are recorded in `conandata.yml`. Conan 2 rejects a one-character
version slug, so the sanctioned `set_version()` mapping keeps the task branch
and directory at `4` while naming the built artifact `cutmp3/4.0`.

## Build

The upstream project is two C translation units built by a plain Makefile.
The recipe invokes the Conan-selected C compiler directly because the Makefile
hard-codes `gcc`, overrides consumer flags, and has a host-specific install
rule. The resulting `cutmp3` is a static PIE with NX, stack protection, and
full RELRO. GNU readline and ncurses are linked from their Conan packages;
`mpg123` is retained as the runtime provider for interactive playback.

## Portability patch

`patches/0001-main.c.patch` replaces fixed `/tmp` and `/dev/shm` templates with
the POSIX `TMPDIR` location, falling back to `/tmp` when the variable is not
set. This preserves all upstream functionality and requires no platform macro.

## Upstream test census

| Evidence | Result |
|----------|--------|
| Test directories named `test`, `tests`, or `testing` | 0 |
| Test/spec source files | 0 |
| Makefile `test` or `check` targets | 0 |
| CTest, pytest, Meson, or Autotools test registration | 0 |
| Upstream tests executed | 0/0 (100%) |

The archive contains 20 regular files. Its Makefile defines build, debug,
install, uninstall, clean, and profiling targets only, so there is no upstream
automated test that can be integrated into `build()`.

## Added tests

- `test_cutmp3.py` generates a deterministic MPEG-1 Layer III stream, checks
  help/version output and metadata parsing, cuts a one-second segment, parses
  the result, and verifies invalid-input rejection.
- `test_ohos_tmpdir.py` is the HarmonyOS-specific test. It verifies that a
  private writable `TMPDIR` is used and cleaned, and that an invalid `TMPDIR`
  is reported instead of silently falling back to a fixed Linux path.

Both tests execute the packaged binary. Native OHOS runs it directly; the
cross-validation profile runs the same static AArch64 PIE through QEMU.

## Dependencies

- `readline/8.3`
- `ncurses/6.6`
- `mpg123/1.33.5`
---

**编译结束**: 2026-09-11 03:59
**最终状态**: built
