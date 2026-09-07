# hopscotch 0.1.2 — native build/test evidence

- Date: 2026-09-04
- Source: `$HOME/tmp/ohc-hopscotch-0.1.2/safe/builds/hopscotch-0.1.2.work/hopscotch-0.1.2`
- Compiler: `/data/service/hnp/bin/clang`; archive tools: `/data/service/hnp/bin/llvm-ar`, `/data/service/hnp/bin/llvm-ranlib`

Command:

```sh
make -C "$SRC" clean
make -C "$SRC" CC=/data/service/hnp/bin/clang \
  AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib -j1
```

Result: exit 0. `build/hopscotch`, `build/libhopscotch.a` and object files were produced.

Upstream test command:

```sh
make -C "$SRC" CC=/data/service/hnp/bin/clang \
  AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib test -j1
```

Result: exit 2; the first error was:

```text
In file included from test/test_hopscotch.c:1:
test/test_hopscotch.h:4:10: fatal error: 'greatest.h' file not found
#include "greatest.h"
```

Test-target statistics (unit: one Make `test` target): `TOTAL=1 PASS=0 FAIL=0 SKIP=0 NOT_RUN=1`. The target did not reach execution. The release tarball's `vendor/greatest.h` is a broken absolute symlink and the external `greatest`/`theft` test dependencies are not installed on this worker. The Conan `test_package` separately runs the public C API consumer and passed; it does not claim the missing upstream property/benchmark coverage.
