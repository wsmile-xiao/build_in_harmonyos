# libsee 1.1.0 — native build/test evidence

- Date: 2026-09-04
- Compiler: `/data/service/hnp/bin/clang`
- Native build directory: `$HOME/tmp/ohc-libsee-1.1.0/native-build`

The upstream CMake source was configured with the required `-fPIC -fno-builtin -nostdlib -nostartfiles` C flags and `-shared` linker flag, then built with one job. The build exited 0 and produced `libsee.so`. The upstream `libsee_test.c` is empty and CMake registers no CTest, so upstream test statistics are `TOTAL=0 PASS=0 FAIL=0 SKIP=0 NOT_RUN=0` (no test exists). The patched source was separately rebuilt with the same flags before the preload run.

The unpatched `LD_PRELOAD=<native-build>/libsee.so true` exploration exited 139/SIGSEGV and remains recorded as the original failure in `exploration.txt`. The OHOS portability patch hides unavailable Annex K `_s` interposers; a rebuilt patched library then ran `/data/service/hnp/bin/bash -c true` with exit 0 and printed real LibSee function statistics. The exact OHOS Conan build also ran the real dlopen/dlsym consumer successfully.
