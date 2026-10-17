# cmospwd 5.0 Adaptation Notes

## Build Environment
- Build system: makefile (single-file `src/cmospwd.c`, two-line upstream Makefile)
- Compiler: clang (HarmonyOS PC aarch64, OHOS 6.0)
- Date: 2026-09-09
- Status: built (pending device preflight)

## Build Steps

Upstream tarball `cmospwd-5.0.tar.bz2` (SHA256 `97f48eb0...2ef32`) unwraps to
`src/cmospwd.c`, `src/Makefile`, `cmospwd.txt`, `COPYING`.
The recipe ignores the upstream Makefile `CC=gcc` assignment and compiles
directly so the toolchain compiler from Conan conf is honored (R33):

```sh
clang -Wall -W -O2 -D__linux__=1 -o cmospwd "src/cmospwd.c"
```

`-D__linux__=1` keeps the Linux-compatible file-decode path active when the
OHOS toolchain does not predefine `__linux__`. Installs `bin/cmospwd` plus
`licenses/cmospwd.txt` and `licenses/COPYING`.

## Issues and Fixes

| # | Issue | Root Cause | Fix |
|---|-------|------------|-----|
| 1 | `outb`/`inb` inline asm fails on aarch64; `sys/io.h`/`ioperm` unavailable | Upstream assumes x86 Linux (`#ifdef __linux__` enables x86-only port I/O) | `0001-cmospwd-c-aarch64-portability.patch`: gate `sys/io.h` and asm port I/O behind `__i386__`/`__x86_64__`, add no-op stubs on other arches; non-x86 `set_permissions()` prints a clear message directing users to `-l`/`-r` backup files and exits 1 |
| 2 | No upstream test suite | Single-target Makefile, no `check`/`test` target, no `tests/` directory | Audited in `test_package/MANIFEST.yml` (`upstream_tests_exist: false` + audit); recipe emits `HMBS_UPSTREAM_TEST_RESULT` with `status:no_tests`; consumer coverage comes from `test_package` |
| 3 | Interactive `wait_key()` blocks automated tests | Full decode runs all modules and pauses every 17 entries | Consumer test uses `-m1` (single module) for the file-decode case and `--help` for the usage case; neither path calls `wait_key()` |
| 4 | `self.conf.get("tools.build:compiler_executables:c", ...)` raises `ConanException: [conf] ... does not exist` on conan 2.30 | Colon sub-key access is not a known conf name; only the dict conf `tools.build:compiler_executables` is registered | Read the dict first (`self.conf.get("tools.build:compiler_executables", default={}) or {}`) then `.get("c", "clang")`, same idiom as `archives/z/zutils/1.15/conanfile.py` |

## Source Changes

- `patches/0001-cmospwd-c-aarch64-portability.patch`: arch-gated portability only, no `__OHOS__` macro in patch lines; substantive stubs with user-facing message (not empty `return 0`).

## Dependencies

None. Single C file using only libc (`stdio`, `stdlib`, `string`, `stdint`, `ctype`).

## Verification

Pending HMBS device preflight (`conan create` on HarmonyOS aarch64):

```sh
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

Expected: build succeeds, `HMBS_UPSTREAM_TEST_RESULT` reports `no_tests` with audit
reason, `test_cmospwd` passes 2/2 (usage + 128-byte file decode with `-m1`),
`HMBS_TEST_PACKAGE_RESULT` reports `discovered:2 passedCount:2`.

## Notes

- Recipe version `5.0` tracks upstream `5.0` (task branch `feat/cmospwd-5`).
- Direct CMOS hardware access cannot work on aarch64 (no x86 I/O ports); supported
  usage on HarmonyOS PC is backup-file analysis (`-l`/`-r`/`-m`), verified by Test 2.
- No `commands.json` change beyond the software-level file for this tool.
