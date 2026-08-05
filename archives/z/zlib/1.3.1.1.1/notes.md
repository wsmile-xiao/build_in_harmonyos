# zlib 1.3.1.1.1 HarmonyOS PC adaptation notes

Issue: #1829
Difficulty: B
Branch: feat/zlib-1.3.1
Target path: archives/z/zlib/1.3.1.1.1

## Summary

`zlib/1.3.1` and `zlib/1.3.1.1` are already published, so this compatibility
fix is packaged as `zlib/1.3.1.1.1`. The source remains upstream zlib 1.3.1.

The package stays static-only because zlib is a system same-name library on
HarmonyOS. To support consumers that link zlib into shared libraries or Python
extension modules, the recipe now builds `libz.a` with `-fPIC`.

## Build

```text
CONFIG_SHELL=/data/service/hnp/bin/bash
CC=<compiler from tools.build:compiler_executables>
CFLAGS=-O3 -fPIC
./configure --static --prefix=/
make -j1
make check
```

## Validation Strategy

The recipe runs upstream `make check`, which builds and runs zlib's official
`example` and `infcover` tests.

The `test_package` verifies two consumer paths:

- `test_zlib` performs a compress/uncompress round trip.
- `zlib_pic_probe` is a shared library linked against `zlib::zlib`; this catches
  the AArch64 non-PIC relocation failure that blocked higher-level consumers.

## Downstream Context

This fix was split out while adapting `gobject-introspection/1.78.1`. That
package builds a Python extension module and failed when static GLib pulled in
the existing non-PIC `zlib/1.3.1` archive:

```text
relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'
```

Downstream packages that need PIC zlib should depend on `zlib/1.3.1.1.1`
instead of the already-published `zlib/1.3.1` or `zlib/1.3.1.1`.

## Verification

True-device single-package CI passed on `10.62.189.79:2222`.

```sh
cd /storage/Users/currentUser/codex-tests/zlib-1829
export CONAN_HOME=$PWD/.conan2-zlib-1829-v3
CI_PACKAGES="archives/z/zlib/1.3.1.1.1" zsh ci/conan/build_and_test.sh
```

Result:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=pass: lib/ has content
```

Log:

```text
/storage/Users/currentUser/codex-tests/zlib-1829/zlib-ci-1829-v3.log
```
