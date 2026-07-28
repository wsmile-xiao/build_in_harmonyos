# plog

`plog` 1.1.11 is a portable, header-only C++ logging library with no
third-party runtime dependencies.

## Conan

```bash
conan install --requires=plog/1.1.11 -r=ohpcd
```

With CMakeDeps, consume the generated interface target:

```cmake
find_package(plog CONFIG REQUIRED)
target_link_libraries(app PRIVATE plog::plog)
```

Then include the public headers:

```cpp
#include <plog/Log.h>
#include <plog/Initializers/ConsoleInitializer.h>
```
