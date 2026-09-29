# Kanzi C++

kanzi-cpp 2.5.3-git20260504 is a snapshot of [Kanzi](https://github.com/flanglet/kanzi-cpp),
a modern, modular and portable lossless data compressor written in C++ (Apache-2.0).
Zero third-party dependencies; CMake build with C++17.

## Conan

```bash
conan install --requires=kanzi-cpp/2.5.3-git20260504 -r=ohpcd
```

Consume the library with CMakeDeps:

```cmake
find_package(kanzi CONFIG REQUIRED)
target_link_libraries(app PRIVATE kanzi::kanzi)
```

Or use the C API directly:

```c
#include <kanzi/api/Compressor.hpp>
#include <kanzi/api/Decompressor.hpp>
```

The package also ships the `kanzi` command line tool
(`kanzi -c -i <in> -o <out.knz>` / `kanzi -d -i <in.knz> -o <out>`).
