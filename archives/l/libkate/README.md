# libkate

Xiph Kate text and karaoke codec library.

```cmake
find_package(kate CONFIG REQUIRED)
target_link_libraries(app PRIVATE kate::kate)
```

The default Conan package is static and includes Ogg integration.
