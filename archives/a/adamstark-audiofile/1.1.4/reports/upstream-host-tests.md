# adamstark-audiofile 1.1.4 Upstream Host Test Report

- Date: 2026-08-06
- Source archive: `AudioFile-1.1.4.complete.tar.gz`
- Source SHA-256: `e3749f90a9356b5206ef8928fa0a9c039e7db49e46bb7f32c3963d6c44c5bea8`
- Source tree: `E:\HarmonyPC\validation\adamstark-audiofile-1.1.4\src-r1\AudioFile-1.1.4`
- Build tree: `E:\HarmonyPC\validation\adamstark-audiofile-1.1.4\host-build-r1`
- Generator: Ninja
- Compiler: GCC 15.2.0 via w64devkit

## Commands

```bash
cmake -S <source> -B <build> -G Ninja -DBUILD_TESTS=ON -DBUILD_EXAMPLES=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build <build> -- -j1
ctest --test-dir <build> --output-on-failure -V -j1
<build>/tests/Tests.exe --list-test-cases
```

## Result

- CTest entries: 1/1 passed
- Doctest test cases: 73/73 passed
- Doctest assertions: 1,739,931/1,739,931 passed
- New consumer tests in this report: 0/0, not applicable

The PR test accounting uses 73/73 for upstream tests. Assertion count is
recorded only as supporting detail.
