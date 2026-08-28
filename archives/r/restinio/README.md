# restinio

RESTinio — C++14 header-only library for building REST/HTTP server applications
on top of Asio. The Conan recipe packages the public headers together with a
bundled standalone-asio 1.28.1 snapshot, and exposes fmt and http-parser as
Conan `requires` so consumers link against the real OpenHarmony PC platform
packages rather than vendored copies.

## Status

| Version | Status |
|---------|--------|
| 0.6.19  | built (header-only + bundled standalone asio + fmt/http-parser requires) |

## License

BSD-3-Clause (restinio), Boost-1.0 (asio snapshot).

## Consumers

```cmake
find_package(restinio REQUIRED)
target_link_libraries(app PRIVATE restinio::restinio)
```

The Conan `requires` chain declares `fmt/8.1.1` and `http-parser/2.9.4`; do
not vendor those sources into a downstream recipe.
