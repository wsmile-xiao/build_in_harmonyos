# W0 Dependency Report — socket-wrapper 1.5.2

Date: 2026-09-02

## Hard runtime dependencies

None. socket_wrapper is a self-contained LD_PRELOAD interposition library
built against libc + libpthread only.

## Test dependencies

| Dependency | Required by | Registry check (R35: actual download) | Status |
|---|---|---|---|
| cmocka/2.0.2 | upstream CTest suite (`find_package(cmocka 1.1.0 REQUIRED)`) | `conan download cmocka/2.0.2 -r=ohpcd --only-recipe` → recipe revision `07881f2c819b9063a0be6ece415bb688` cached; `conan install --requires=cmocka/2.0.2 -r=ohpcd -pr:h ohos-aarch64` → binary `21b17f8b2bc0e9511e276e3d57a23893067cefe5` "Already installed" | ✅ published, binary usable |

## Conclusion

All dependencies published. The recipe runs the upstream CTest suite with
`cmocka/2.0.2` as `test_requires` (default `with_upstream_tests=True`).

## Platform prerequisites (not Conan packages)

- POSIX dynamic loader with LD_PRELOAD support ✅ (validated by test_package)
- A short writable directory for SOCKET_WRAPPER_DIR (AF_UNIX sun_path limit;
  /data/storage/el2/base/temp works, HMDFS /storage paths are too long or deny
  AF_UNIX bind)
- OHOS signing tools for build-tree tests and packaged .so files
