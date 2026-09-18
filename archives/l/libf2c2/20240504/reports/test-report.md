# libf2c2 20240504 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 (native build and run on the device)
- Clang 15.0.4 (`/data/service/hnp/bin/clang`, target `aarch64-unknown-linux-ohos`)
- Conan 2.29.1, profile `ci/conan/profiles/ohos-aarch64`
- Private task-owned `CONAN_HOME` under `~/ws/tmp/`, `tools.build:jobs=2`

## Verification

| Step | Command | Result |
|------|---------|--------|
| Recipe verification | `conan-verify libf2c2 20240504` | exit 0 — G0/G1/G2/G3/G4 PASS, L2/L4/L5 PASS |
| Local CI simulation (W3) | `build_and_test.sh libf2c2/20240504` | exit 0 — L0 pass, L1 pass, L1e pass, L2 skip, L4 pass, L5 pass |

W3 gate detail:

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
```

L1e (destructive negative test, R34) moved `lib/` and `include/` away, the
test then failed to build, and the gate confirmed the test genuinely depends
on the package — it is not a shell that passes without the library.

## Test case comparison

Counting unit: **one assertion** — a single boolean check performed by a
test program, as printed by `test_main` (`ok - <description>`) or by the exit
status of `test_startup`.

| Set | Source | Cases | PASS | FAIL | SKIP |
|-----|--------|------:|-----:|-----:|-----:|
| Upstream | `libf2c.zip` | 0 | 0 | 0 | 0 |
| HarmonyOS-specific (test_package) | `test_main.c` (27) + `test_startup.c` (1) | 28 | 28 | 0 | 0 |
| Total | | 28 | 28 | 0 | 0 |

- Upstream pass rate: 0/0 — `libf2c.zip` ships no runnable test program, so
  there is no upstream entry point to run and no upstream denominator. The
  only test hook in the archive is `makefile.u`'s `check` target, which
  compares source checksums against the bundled `xsum0.out` and needs the
  `xsum` tool; `xsum.c` ships with the separate f2c *compiler* source
  (netlib `src.tgz`), not with this archive, so it cannot be executed here.
  Source integrity is enforced instead by the pinned sha256 in
  `conandata.yml`, which is a stronger check on the same property.
- Adapted pass rate: 28/28 (100%), counted as HarmonyOS-specific tests, i.e.
  outside the upstream denominator.
- Test programs: 2 (not counted as assertions).

## test_package detail

`test_main` — an ordinary C consumer that includes the installed `f2c.h`,
links the package through `find_package(libf2c2)` and calls the run time the
way translated code does. 27 assertions:

| Group | Assertions | What is checked |
|-------|-----------:|-----------------|
| Intrinsic functions | 6 | `d_prod`, `pow_dd`, `d_lg10`, `i_nint` (positive and negative), `d_sign` |
| Character-string run time | 7 | `s_cmp` equality/ordering/blank padding, `i_indx` hit and miss, `s_copy` blank padding and truncation |
| `-trapuv` helper | 2 | `_uninit_f2c` fills an uninitialised REAL and DOUBLE PRECISION with NaN |
| List-directed file I/O | 12 | `f_open` → `s_wsle` → `do_lio` (REAL and INTEGER) → `e_wsle` → `f_clos` → reopen → `s_rsle` → `do_lio` → `e_rsle` → `f_clos`, then both values compared against what was written |

`test_startup` — an f2c-translated-program consumer: it defines `MAIN__` and
has no `main()` of its own, so the entry point, `f_init()` and the
`atexit(f_exit)` flush all come from the library. 1 assertion (exit status 0
after a list-directed write of `12345` to unit 6, which is printed as
` 12345`). This consumer is what exercises the `patches/0002` weak-symbol
change from the translated-program side.

Both are executed by `test_package/conanfile.py`'s `test()` during
`conan create`; the full output is in `reports/w3-local-ci.log`.

## Key issue analysis

### Issue 1: `fpu_control.h` missing (glibc-only header)

```
uninit.c:236:10: fatal error: 'fpu_control.h' file not found
```

`fpu_control.h` is a glibc header. The OHOS sysroot is musl-based, but the
OHOS clang driver still defines `__linux__`, so `uninit.c`'s
`#ifdef __linux__` block entered a glibc-only path. Fixed by
`patches/0001`, which narrows the guard to
`defined(__linux__) && defined(__GLIBC__)`; the musl build then uses
upstream's own `ieee0() {}` fallback. Only `-trapuv`'s FP-exception
unmasking is unavailable there, exactly as on every other non-glibc system.

### Issue 2: undefined `MAIN__` in the shared library

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: MAIN__
```

Upstream compiles `main.c` into the library, while `MAIN__` is supplied by
the translated program, leaving an undefined symbol in `libf2c.so`. lld and
current binutils reject linking an executable against such a shared object.
`patches/0002` gives `main()` and `MAIN__` weak definitions so a translated
program's strong `MAIN__` (and any C program's own `main`) still wins. This
is the same defect Debian tracks as #826253.

## Known limitations

- `libf2c_i2` (the `f2c -i2` ABI) is not built. No package in this
  repository provides the f2c compiler, so nothing can generate `-i2` code,
  and the two ABIs export identical symbol names and cannot share a link
  line. Building it additionally is a one-line change to `build()`
  (`-Df2c_i2`, output name `libf2c_i2.so.2`).
- The exported symbol set is 281 symbols against Debian's 283; the
  difference is entirely Debian's own downstream patches
  (`i_dceiling`/`i_sceiling`/`i_len_trim` from `0004-add-clapack-files.patch`
  and `unsupported_error` from `0003-C-tweaks.patch`), plus `_init`/`_fini`
  which this build exports and Debian's listing does not.

## Environment detail

```
libf2c2/20240504@ohpcd/stable
profile: ci/conan/profiles/ohos-aarch64   (os=OHOS, os.version=6.0, arch=armv8, clang 15)
CFLAGS:  -O2 -fPIC -DNON_UNIX_STDIO
link:    clang -shared -Wl,-soname,libf2c.so.2 -o libf2c.so.2.1 <objects> -lm
```

*Report generated 2026-09-18.*
