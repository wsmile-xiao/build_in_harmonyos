# libzimg 3.0.6 adaptation notes (autotools build, task #13534)

## Scope

- Target: zimg release-3.0.6, packaged as `libzimg/3.0.6`
- Platform task: #13534, branch `feat/libzimg-3.0.6`, claimer calbee21
- Upstream: https://github.com/sekrit-twc/zimg (tag `release-3.0.6` — note
  the `release-` prefix, not `v`)

## Why a second package (zimg vs libzimg)

`archives/z/zimg/3.0.6` (merged earlier, published as `zimg/3.0.6` on the
registry) bypassed autotools: the release tarball ships only autotools
inputs and that recipe compiled `src/zimg` directly with clang++, skipping
the upstream test suite. Task #13534 asks for the autotools build with the
upstream test suite actually run. CI L0n requires the branch name to equal
`<pkg>-<version>` and the platform branch is `feat/libzimg-3.0.6`, so this
recipe is `libzimg/3.0.6` in `archives/l/libzimg/3.0.6`. The registry holds
no `libzimg/3.0.6`, so R37/L0j is clean. Both packages install the same
`libzimg.so` / headers and stay side-by-side installable.

## Build strategy (verified locally on the aarch64/OHOS worker)

The release tarball carries `configure.ac` / `Makefile.am` / `autogen.sh`
but no generated configure. The recipe bootstraps with
`tool_requires automake/1.18 + libtool/2.5.4.1` (registry) and the hnp
`autoconf` from PATH:

```
aclocal --force -I m4
autoconf -o configure configure.ac
libtoolize --copy --force --install   # _lt_pkgdatadir staged from the package
automake --add-missing --copy --no-force
```

Notes:

- The conan automake package's `bin/aclocal` must be used (an aclocal 1.17
  from `~/usr/local/bin` against the 1.18 share dir dies with
  `@am_AUTOM4TE@: inaccessible or not found`).
- `libtoolize` needs `_lt_pkgdatadir` staged (build-aux + m4 + libltdl)
  from the libtool package (gmime 3.0.6 / abiword pattern).
- After bootstrap the generated `configure` is checked for unexpanded
  macros (AX_CHECK_COMPILE_FLAG / AX_PTHREAD / AM_INIT_AUTOMAKE / LT_INIT)
  to fail fast instead of at runtime.

configure invocation:

```
./configure --build=aarch64-linux --host=aarch64-linux \
            --enable-unit-test STL_LIBS=-lc++ [--enable-shared|--enable-static]
```

- Device-native build: the worker is itself aarch64/OHOS, so both triplets
  are `aarch64-linux`; `AC_CANONICAL_HOST` sees `aarch64` and selects the
  ARM backend (ZIMG_ARM + the 26 NEON unit cases).
- `STL_LIBS=-lc++` overrides the `-lstdc++` default in `zimg.pc.in`'s
  `Libs.private` for the OHOS libc++ runtime.
- `--enable-unit-test` runs the upstream cmake sub-build of gtest inside
  configure (exactly the upstream CI shape).

## E114/E206 umask fix

The generated `configure` writes `umask 077` before running config.status
mktemp temp dirs; HMDFS blocks those permission bits ("can't create
./confXXXXXX/subs1.awk: Permission denied"). The recipe rewrites it to
`umask 022` after bootstrap (gmime precedent). Verified on this worker.

## Upstream unit tests (hard requirement)

`--enable-unit-test` builds `test/unit_test` via gtest plus the bundled
musl-libm reference library (linked by test/main.cpp for exact FP
references). On aarch64 the suite registers **122 cases**
(96 generic + 26 NEON; counted with
`./test/unit_test --gtest_list_tests`):

- api (3), colorspace (8+12), depth (6+7), graph (10+34), resize (7+9)
- colorspace NEON (2), depth NEON (8+8+2), resize NEON (6)

Local run result (worker, 2026-09-16): **122/122 PASSED** in ~52s;
`make check` reports `PASS: 1 / FAIL: 0` at the automake level.

Two OHOS specifics needed for the run:

1. `LD_LIBRARY_PATH` must include the SDK
   `.../llvm/lib/aarch64-linux-ohos` dir (libc++_shared.so); the CI
   profile only prepends `.../llvm/lib`. The recipe prepends it in
   `generate()` via `libzimg_ohos_buildenv`.
2. googletest must be ≤1.14.0: gtest 1.15+ requires C++17 while zimg
   builds with `CXXSTD=c++14` (configure probes c++14 first). v1.14.0 is
   shipped as the second conandata source and unpacked into
   `test/extra/googletest` (the empty submodule slot).
   Proven failure with 1.17.0:
   `gtest-port.h:273: error: C++ versions less than C++17 are not supported.`

## Packaging

- `make install` ships `zimg.h` / `zimg++.hpp`, `libzimg.so.2.0.0` (+soname
  links) or `libzimg.a`, `zimg.pc` (with `Libs.private: -lc++`), COPYING.
- `.la` files are removed (build-machine prefixes; conan uses cpp_info).
- `share/` doc noise is dropped.
- Shared libs are OHOS code-signed in `package()` (llvm-objcopy strip
  `.codesign` + binary-sign-tool self-sign, same flow as the zimg recipe)
  so test_package can link and run on an OHOS host.

## Consumer test (test_package)

`test.cpp` exercises the public C API end to end: version/API checks,
resize graph build (16x16→8x8 float grey) + tmp size query, and on OHOS an
end-to-end depth conversion (BYTE full-range → WORD limited-range, the
aarch64 NEON depth kernel path) with limited-range clamp verification
(output within [16, 235*257]). Builds via cpp_info (-lzimg -lm -pthread
-lc++), runs under VirtualRunEnv.

## W0 dependency check

No runtime dependencies (pure C++ math library; pthread/m from the
system). Build tools: automake/1.18 + libtool/2.5.4.1 verified published
on the ohpcd registry (conan download --only-recipe). gtest is not a
conan dependency — the upstream build manages it from the official
tarball.

## Reproduction

```
conan create archives/l/libzimg/3.0.6 \
    -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
    -pr:b=$HOME/.conan2/profiles/ohos-aarch64 --build=missing
```
