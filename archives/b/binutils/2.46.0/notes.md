# binutils 2.46.0 HarmonyOS PC adaptation notes

## Scope and contest path

- Package: native GNU Binutils command-line suite for HarmonyOS PC aarch64.
- Recommended contest path: C, pending the committee's high-difficulty review.
- Definitive path-C criterion: complex assembly/toolchain architecture. The official
  archive has 29,637 entries, 8,815 `.s` files and 7 `.asm` files, with BFD,
  opcodes, gas, ld, libctf, libsframe and gprof components.
- Runtime Conan requirements are empty, so a large dependency chain is not claimed.
- The only Issue/PR title prefix for this candidate is `【高难度挑战】`.

## Upstream identity

- Project: `https://www.gnu.org/software/binutils/`
- Repository: `https://sourceware.org/git/binutils-gdb.git`
- Tag / peeled commit: `binutils-2_46` /
  `49d4d3fafa4ec4ff5a3460d91d5b1ed5286487db`
- Archive: `https://ftp.gnu.org/gnu/binutils/binutils-2.46.0.tar.gz`
- Archive size: 53,967,419 bytes
- SHA256: `8608fe44ab7de645f6ad0a898313b75338842490d609adb85c9fb2827c376af2`
- License: GPL-3.0-or-later, with component notices retained.

## W0 and W0b

Runtime `required: []`. Target-native tests use build-context packages only:

| Reference | W0 result |
|---|---|
| `dejagnu/1.6.3.1` | recipe/package available; fresh final cache resolved it |
| `expect/5.45.4` | rebuilt in final cache; upstream 28 PASS / 1 SKIP / 0 FAIL |
| `tcl/8.6.14` | resolved in final cache |
| `zlib/1.3.1` | Expect transitive dependency; rebuilt in final cache |

The 2026-05-25 historical binutils archive recorded a native device build but
did not contain a Conan recipe, fixed source hash, consumer test or complete test
inventory. Revalidated findings:

1. Release `config.sub` already accepts `linux-ohos`; no config.sub patch is used.
2. `config.guess` needs a focused HarmonyOS/OpenHarmony uname branch.
3. Fourteen generated configure scripts need `umask 022` for HMDFS config.status
   temporary directories.
4. gprofng's collector uses Linux-specific runtime facilities and is explicitly
   disabled rather than silently omitted.

## Portability implementation

- Patches 0001-0015 cover config.guess and configure/HMDFS behavior.
- Patches 0016-0020 route cached shell helpers through the configured HNP bash,
  use DejaGNU's pipe/file channels, and preserve normal Makefile behavior elsewhere.
- Patch 0021 copies the exact SFrame DATA fixtures where HMDFS symlinks are not
  reliable.
- Patch 0022 uses `send_log --` so a negative process result is logged as data and
  does not abort the Tcl driver.
- Patch 0023 uses `cp -f` when a versioned DSO replaces an already loaded fixture.
- Patch 0024 makes Clang select the candidate GNU ld explicitly in libctf.
- Patch 0025 copies test ld/as executables on OHOS and uses the candidate GNU as
  only for `compress.exp`; it restores compiler flags before the next driver.
- Clang build/test objects use `-fno-addrsig`, documented by draft E547.
- Make/install are serial because HMDFS rejects the GNU make FIFO jobserver path.
- A native launcher reads DejaGNU's script from HMDFS and invokes the interpreter.
- A tmpfile preload is verified with write/read/seek/close before long tests.

No production C/C++ behavior and no expected output are rewritten.

## Native test deployment

GNU ld output requires normal platform signing before execution. The exported
`ohos-test-sign.py/.exp` helper is intentionally narrow:

- accepts only ELF64 little-endian AArch64 ET_EXEC/ET_DYN under the current
  suite's resolved `tmpdir`;
- signs the requested program and local `DT_NEEDED` closure found in the suite,
  program directory or tmpdir;
- adds only explicit literal-dlopen fixtures, including `pr21964-2b.so` for
  `pr21964-2`;
- removes an old `.codesign` section before signing a relinked file;
- never rewrites a verdict or scans unrelated directories.

Custom RPATH/RUNPATH directories outside those local conventions remain outside
the helper's lookup scope.

## Test inventory and final result

The release has 386 DejaGNU `.exp` files. Seven gprofng files belong to the
disabled collector. Of 379 enabled files, 367 are executed drivers and 12 are
support files.

| Suite | Inventory / drivers | PASS | FAIL | XFAIL | UNRESOLVED | UNTESTED | UNSUPPORTED |
|---|---:|---:|---:|---:|---:|---:|---:|
| binutils | 37 / 34 | 273 | 1 | 2 | 0 | 2 | 8 |
| gas | 145 / 142 | 1239 | 0 | 0 | 0 | 0 | 10 |
| ld | 187 / 184 | 1721 | 34 | 13 | 0 | 2 | 182 |
| libctf | 6 / 4 | 18 | 0 | 0 | 0 | 0 | 3 |
| libsframe | 4 / 3 | 168 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **379 / 367** | **3419** | **35** | **15** | **0** | **4** | **203** |

Normal DejaGNU rate: `3419/(3419+35+0)=98.99%`.

Libiberty separately passes 930/930 checks across seven Make targets. gprof has
two source entries but `gprof_cv_sys_native=no` on this SDK, so its Automake
summary is 0 discovered / 0 executed / 0 failed; this is an exclusion, not a pass.
All 35 FAIL occurrences are retained and machine-mapped in
`ohos-failure-analysis.md`; review of their log contexts and the recorded
control runs found zero failures caused by the current adaptation.

## Consumer contract

The common test script performs an installed-package ELF workflow with `as`,
`readelf`, `objdump`, `nm`, `ar`, `ld` and `strip`, then checks a missing-input
negative control. It has 13 assertions. Native OHOS testing adds three real
executions after GNU ld, objcopy and strip transformations. Final result: 16/16.

## Final evidence identity

- Device job: `j039`, 2684.96 seconds, exit 0.
- Isolated paths: `device-bundle-r6`, `final-cache39`, `final-build39`.
- Input bundle SHA256:
  `61f2ab642e0405787a1af1fa34e47b9e12281eb9fd1d8a93d509348fc2beec79`.
- Evidence archive SHA256:
  `8efd26e9be91e44d4deb7eb53a4d85ebc9320dc54481f00d392936b183d7c6f3`.
- Result manifest: 138 files verified.
- Package reference:
  `binutils/2.46.0#11a4a9b63a85bc14b6f4edc65fc4fdfe:6b129b068851896169fae42d399fa922d239ce8a#79f95fb4875a2b5b802d4eaec2ee7349`.
- Package contents: 453 files, 65,975,560 bytes.

Historical final20 and rejected final34 results remain available. final34 applied
external GNU as to all LD drivers and introduced `mbind2a/b`; it was rejected by
the failure classifier. A device-session interruption left final36 incomplete and
explicitly marked rc=130; it is not acceptance evidence.

## Remaining process gates

Task `#3485` was claimed by `sawakage` at 2026-09-08 19:59:25 CST. The feature
branch was rebased onto official `main=7285d0428`; the 40 recipe/test inputs are
byte-identical to the final39 device bundle. The finish-generated W3 state records
exit 0 with log SHA256
`e8909b256f8190a1451d05a83527b4bd4d053c7d2b5c0fb84019eeb6ab068b24`.
The remaining external steps are final W4, Issue/PR creation and association,
official CI and AI review, and committee review. Engineering evidence supports
path-C candidacy but does not grant the contest classification.
