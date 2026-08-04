# dyld-headers

Public header files from Apple's open-source dynamic linker distribution.

## Packaged Content

The package follows the Homebrew formula scope and installs all 14 files from
the upstream `include/` directory. It does not build or emulate the Apple dyld
runtime.

Portable declarations such as Mach-O chained-fixup layouts can be consumed on
OHOS. Interfaces that include Apple platform frameworks remain available for
source inspection and Apple-targeted builds, but they require the corresponding
Apple SDK headers and runtime.

## Conan

```cmake
find_package(dyld-headers CONFIG REQUIRED)
target_link_libraries(app PRIVATE dyld-headers::dyld-headers)
```

## References

- [Upstream dyld repository](https://github.com/apple-oss-distributions/dyld)
- [Homebrew formula](https://formulae.brew.sh/formula/dyld-headers)
