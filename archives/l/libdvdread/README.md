# libdvdread

Low-level DVD access library from VideoLAN.

```cmake
find_package(dvdread CONFIG REQUIRED)
target_link_libraries(app PRIVATE dvdread::dvdread)
```

The default Conan package is static and does not require `libdvdcss`.
