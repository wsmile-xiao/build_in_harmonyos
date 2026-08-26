# zlib 1.3.1.1.1 HarmonyOS PC adaptation notes

Issue: not tracked in this round
Difficulty: B
Branch: fix/zlib-1.3.1.1.1
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

True-device single-package shadow CI passed on `the OHOS device runner`.

```sh
JOB=<isolated-zlib-job>
. "$JOB/env.sh"
EXTRA_PATH=/data/service/hnp/bin:/data/service/hnp/cmake.org/cmake_4.1.2/bin:$HOME/usr/local/bin:$HOME/.local/bin:$HOME/ohpc-ci-shadow/python-user/bin
sh "$HOME/bin/ohos-test-runner.sh" \
  --user codex \
  --lib zlib \
  --task zlib-1.3.1.1.1-r3-pathfix-20260825 \
  --mode smoke \
  --try-lock \
  --path "$EXTRA_PATH" \
  --workdir "$CI_REPO_ROOT" \
  -- zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
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
codex-zlib-zlib-1.3.1.1.1-r3-pathfix-20260825-20260825-193939-59953/logs
```
