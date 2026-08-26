# zlib static PIC archive for OHOS system libz

## Error signature

Downstream shared-library or Python-extension consumers fail when a static zlib archive was built without PIC objects:

```text
relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'
```

This can appear after GLib, cairo, gobject-introspection, or other libraries pull static zlib into a DSO.

## Root cause

HarmonyOS already provides a system `libz.so`. A Conan zlib package should avoid publishing another shared `libz.so`, because that can collide with system loader paths. But a default static `libz.a` can still be unsafe for DSO consumers if the archive objects were not compiled with `-fPIC`.

## Recommended solution

Package zlib as static-only and force PIC objects:

```sh
CONFIG_SHELL=/data/service/hnp/bin/bash \
CC=/data/service/hnp/bin/clang \
CFLAGS="-O3 -fPIC" \
/data/service/hnp/bin/bash ./configure --static --prefix=/
make -j1
make check
```

The Conan package should provide `lib/libz.a`, headers, and `zlib.pc`, but not a competing `libz.so`.

## Validation

For `zlib/1.3.1.1.1`, single-package shadow CI passed with:

```sh
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

## Forbidden shortcuts

Do not publish a Conan `libz.so` on OHOS just to fix a DSO link. Do not drop `-fPIC` from the static zlib archive. Either shortcut can move the failure from build time to runtime.
