# oystr 0.2.0 — native build/test evidence

- Date: 2026-09-04
- Patched source snapshot: `/storage/Users/currentUser/.conan2/p/b/oystr001959f499649/b`
- Conan toolchain: `/storage/Users/currentUser/.conan2/p/b/oystr001959f499649/b/build/Release/generators/conan_toolchain.cmake`
- Independent build directory: `/storage/Users/currentUser/tmp/ohc-oystr-0.2.0/native-build`
- Compiler: `/data/service/hnp/bin/clang++` (clang 15.0.4), libc++
- CMake mode: `CMAKE_SYSTEM_NAME=Linux`, `CMAKE_SYSTEM_PROCESSOR=aarch64`, `CMAKE_POLICY_VERSION_MINIMUM=3.5`, `oystr_DEVELOPER_MODE=ON`, `BUILD_TESTING=ON`

Commands:

```sh
cmake -S /storage/Users/currentUser/.conan2/p/b/oystr001959f499649/b \
  -B /storage/Users/currentUser/tmp/ohc-oystr-0.2.0/native-build \
  -G "Unix Makefiles" \
  -DCMAKE_TOOLCHAIN_FILE=/storage/Users/currentUser/.conan2/p/b/oystr001959f499649/b/build/Release/generators/conan_toolchain.cmake \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -Doystr_DEVELOPER_MODE=ON -DBUILD_TESTING=ON \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /storage/Users/currentUser/tmp/ohc-oystr-0.2.0/native-build --parallel 1
ctest --test-dir /storage/Users/currentUser/tmp/ohc-oystr-0.2.0/native-build --output-on-failure --parallel 1
```

Result: configure, build, and CTest exited 0. Upstream CTest discovered one test and passed: `TOTAL=1 PASS=1 FAIL=0 SKIP=0 NOT_RUN=0` (`oystr_test`).

Native behavior checks also exited 0: a PTY-backed file search reported `needle`, and `printf ... | /storage/Users/currentUser/tmp/ohc-oystr-0.2.0/native-build/oy needle` reported `needle` on stdin (`file=PASS stdin=PASS`). Conan `test_package` repeats those two real command assertions and passed.
