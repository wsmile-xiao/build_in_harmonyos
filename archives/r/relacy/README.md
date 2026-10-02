# Relacy Race Detector

Relacy is a header-only C++ library for exhaustively checking synchronization algorithms under relaxed memory models.

Upstream: https://github.com/dvyukov/relacy

The Conan package installs headers under `include/relacy` and exposes the `relacy::relacy` CMake target. It defines `RELACY_USE_PTHREAD_FIBERS` to use the OHOS-compatible cooperative pthread scheduler backend.

```cpp
#include <relacy/relacy.hpp>
```
