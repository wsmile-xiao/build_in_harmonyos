# kainjow Mustache

kainjow Mustache 4.1 is a zero-dependency, header-only Mustache implementation requiring C++11 or newer.

## Conan

```bash
conan install --requires=kainjow-mustache/4.1 -r=ohpcd
```

Include the packaged header directly:

```cpp
#include <mustache.hpp>
```

With CMakeDeps, consume the generated target:

```cmake
find_package(kainjow-mustache CONFIG REQUIRED)
target_link_libraries(app PRIVATE kainjow-mustache::kainjow-mustache)
```

The package intentionally contains no static library, shared library, or command-line executable.
