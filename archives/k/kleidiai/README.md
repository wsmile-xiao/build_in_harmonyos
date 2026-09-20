# KleidiAI

KleidiAI 1.19.0 is an aarch64-only static library of Arm-optimized
micro-kernels (packing, matrix multiplication, quantization, depthwise
convolution) for AI/ML inference on Arm CPUs. It has no external runtime
dependencies and is distributed under the Apache-2.0 license.

## Conan

```bash
conan install --requires=kleidiai/1.19.0 -r=ohpcd
```

## CMake

Consume the exported CMake target:

```cmake
find_package(KleidiAI CONFIG REQUIRED)
target_link_libraries(app PRIVATE KleidiAI::kleidiai)
```

Include the common header (plus the specific micro-kernel headers you use):

```cpp
#include "kai/kai_common.h"
```

The package contains a static library (`libkleidiai.a`) and the `kai/` headers.
