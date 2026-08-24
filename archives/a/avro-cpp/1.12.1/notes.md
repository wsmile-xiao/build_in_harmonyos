# avro-cpp 1.12.1

Apache Avro C++ is built from the `lang/c++` CMake project as a static Conan
library. The OHOS armv8 validation built `libavrocpp_s.a`, `avrogencpp`, and
seven upstream test targets. The consumer `avro_schema_parse` test passed.

The recipe uses Boost 1.84.0, zlib 1.3.1, and fmt 8.1.1. The portability patch
maps the upstream fmt target `fmt::fmt-header-only` to the available
`fmt::fmt` target and `ZLIB::ZLIB` to Conan CMakeDeps' `zlib::zlib` target.

The supplied device summary did not include the upstream `ctest` pass count;
the version manifest deliberately leaves that count unclaimed until the full
device log is available.

```bash
conan create archives/a/avro-cpp/1.12.1 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```
