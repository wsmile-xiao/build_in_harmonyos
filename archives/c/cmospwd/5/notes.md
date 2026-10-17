# cmospwd 5 Adaptation Notes

## Version key

The platform task `#6532` asks for `cmospwd 5`. Upstream (cgsecurity.org) publishes no
git tag and no separate `5` artifact: the only 5.x release is
`https://www.cgsecurity.org/cmospwd-5.0.tar.bz2` (sha256 `97f48eb0...2ef32`, verified by
`sha256sum` on a local download) and the program banner prints
`CmosPwd - BIOS Cracker 5.0, October 2007`. This recipe therefore ships exactly those
bytes — no `master`/`main` substitution and no invented source.

Conan cannot export a one-character version: `RecipeReference` validation in
`conan/api/model/refs.py` applies `^[a-z0-9_][a-z0-9_+.-]{1,100}\Z`, so `cmospwd/5`
fails at export. Measured on the device with conan 2.29.1:

```
======== Exporting recipe to the cache ========
ERROR: Invalid package version '5'
```

`5.0` is not available either — that key is already published in the artifact registry by
`archives/c/cmospwd/5.0` (merged 2026-09-16 by another contributor, same tarball), and
re-using it would be a same-version recipe change. So, following the merged precedent
`archives/c/cronic/3` (artifact `cronic/v3`) and `archives/r/rapidhash/3`
(`rapidhash/v3`), the task-card directory and the `feat/cmospwd-5` branch stay `5` while
`set_version()` names the built artifact **`cmospwd/v5`**. A literal
`version = "..."` attribute is deliberately absent because CI `L0m` cross-checks such an
attribute against the version directory; `L0j/R37` and `L0k/R38` both key on the
directory name, which stays `5`.

## Build Environment
- Build system: makefile (single-file `src/cmospwd.c`, five-line upstream Makefile)
- Compiler: clang (HarmonyOS PC aarch64)
- Date: 2026-09-20
- Status: built

## Build Steps

The tarball unwraps to `src/cmospwd.c`, `src/Makefile`, a prebuilt x86 `src/cmospwd`,
vendored `src/ioperm-0.4-patched/` module sources, `cmospwd.txt` and `COPYING`.
Upstream `Makefile` pins `CC=gcc`, so the recipe compiles directly and honours the
toolchain compiler from the Conan conf (R33):

```sh
clang -Wall -W -O2 -D__linux__=1 -o cmospwd "src/cmospwd.c"
```

`-D__linux__=1` keeps the Linux-compatible file-decode path active on toolchains that do
not predefine it. Installs `bin/cmospwd` plus `licenses/cmospwd.txt` and
`licenses/COPYING`.

## Issues and Fixes

| # | Issue | Root Cause | Fix |
|---|-------|------------|-----|
| 1 | `outb`/`inb` inline asm fails on aarch64; `sys/io.h`/`ioperm` unavailable | Upstream assumes x86 Linux (`#ifdef __linux__` enables x86-only port I/O) | `0001-cmospwd-c-aarch64-portability.patch` (byte-identical to the one already merged for 5.0): gate `sys/io.h` and asm port I/O behind `__i386__`/`__x86_64__`, no-op stubs elsewhere; non-x86 `set_permissions()` prints a clear message pointing at `-l/-r` backup files and exits 1 |
| 2 | No upstream test suite | Single-target Makefile, no `check`/`test` target, no `tests/` directory | Audited in `test_package/MANIFEST.yml` (`upstream_tests_exist: false` + audit); recipe emits `HMBS_UPSTREAM_TEST_RESULT` with `status:no_tests` |
| 3 | Interactive `wait_key()`/`getchar()` can hang an automated run | Full decode pauses every 17 modules; `-k`/`-r` prompt for a digit and loop forever on EOF | Consumer tests only use `-l`, `-m<mask>` and `--help`, and every invocation runs with stdin from `/dev/null`; `-k`/`-r`/`-d` are never invoked |
| 4 | `self.conf.get("tools.build:compiler_executables:c", ...)` raises on modern conan | Colon sub-key access is not a registered conf name | Read the dict then `.get("c", "clang")`, as already merged for 5.0 |

## What this version adds over the 5.0 recipe

The recipe shape is the merged 5.0 one; the consumer suite is rebuilt around what the
binary actually computes, because 5.0 only asserted that the banner and one module
header appear:

- `-m` is a **digit mask over `tbl_func[]`**, not a module number:
  `for(i=0; argv[m][i+2] && i<nbr_func; i++) if(argv[m][i+2]=='1') tbl_func[i]();`.
  `-m2` therefore runs *nothing*, `-m01` runs module 2 (`ami_old`), `-m11` runs modules
  1 and 2. Three tests pin this down.
- Two **known-plaintext decode** cases. `acer()` reads 7 bytes at offset `0x100` and
  applies `ALGO_ACER` (`>>1`, ASCII mode), so a 512-byte backup holding `0x82,0x84`
  there must print `[AB]`. `phoenix_1_03()` reads `cmos[0x61]` bytes from `0x62` and
  applies `ALGO_PHOENIX_ADD` (`+0x20`), so `0x60=0, 0x61=2, 0x62=0x21, 0x63=0x22`
  must also print `[AB]`. Both expectations were confirmed by compiling the same
  `cmospwd.c` with a host gcc before being written as assertions.
- A **negative control**: the phoenix vector decoded through `acer`'s offsets must *not*
  print `[AB]`, which rules out an assertion that passes by echoing.
- The **aarch64 hardware branch** is asserted, not assumed: with no arguments the binary
  must exit non-zero and print the portability patch's `x86 I/O ports ... use -l/-r`
  guidance (compiled `#if defined(__i386__)||defined(__x86_64__)` so the same test stays
  meaningful on x86).
- Error path (`Unable to read` + non-zero exit) and installed-artifact presence.

## Dependencies

None. Single C file using only libc (`stdio`, `stdlib`, `string`, `stdint`, `ctype`).

## Verification

Device run, isolated cache so the shared `~/.conan2` stays read-only:

```sh
export CONAN_HOME="$HOME/work/psj/ch-cmospwd"
conan create archives/c/cmospwd/5 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

Expected: `CREATE_EXIT:0`, `HMBS_UPSTREAM_TEST_RESULT` with `status:no_tests`, and
`test_cmospwd` printing `TOTAL=24 PASS=24 FAIL=0` / `ALL TESTS PASSED`.
Upstream-test absence was re-checked on the device with `make -n check`.

## Notes

- Direct CMOS hardware access cannot work on aarch64 (no x86 I/O ports); the supported
  usage on HarmonyOS PC is backup-file analysis (`-l` with `-m<mask>`), which is exactly
  what the decode tests exercise.
- `commands.json` gains a `5` entry (L0k/R38 requires the version key to be present);
  the `5.0` entry is kept.
