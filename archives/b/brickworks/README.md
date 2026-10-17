# brickworks

Brickworks is a music DSP toolkit that supplies the fundamental building
blocks for creating and enhancing audio engines on any platform (by
Stefano D'Angelo and Paolo Marrone, Orastron Srl).

## OpenHarmony adaptation

brickworks is a **header-only** C library — all functionality lives in the
59 headers under `include/bw_*.h`; there is no library `.c` source outside
the `test/` directory. The Conan recipe packages the headers into
`include/` and exports a single header-library package id. The consumer
`test_package` compiles a program against the real brickworks API
(`bw_absf` / `bw_pow2f` / `bw_clipf` from `bw_math.h`) to validate the
package on the OHOS aarch64 clang-15 toolchain.

Upstream tests: `test/bw_math.c` runs 1428 assertions against the `bw_math`
routines — all 1428 pass on the OHOS clang-15 toolchain.

License: GPL-3.0 (see `LICENSE`; `include/bw_rand.h` contains
public-domain code, per the upstream README).

## Consumer usage

```c
#include <bw_math.h>

float x = bw_absf(-3.5f);      /* 3.5f */
float y = bw_pow2f(3.f);       /* ~8.f */
float z = bw_clipf(2.f, 0.f, 1.f);  /* 1.f */
```

```cmake
find_package(brickworks CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE brickworks::brickworks)
```