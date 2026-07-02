# Test Report — mac 12.60 (Monkey's Audio)

## Build Information

| Item | Value |
|------|-------|
| Software | Monkey's Audio (mac) |
| Version | 12.60 |
| Build System | cmake |
| Compiler | clang/clang++ 15.0.4 |
| Target | aarch64 (OpenHarmony) |
| Date | 2026-07-02 |

## Build Steps

1. `curl -kL -o MAC_1260_SDK.zip https://monkeysaudio.com/files/MAC_1260_SDK.zip` (SSL bypass)
2. `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX .` — success
3. `make -j2` — success (100% built, NEON SIMD enabled)
4. `make install DESTDIR=$TEST_PREFIX` — staged install
5. `make install` — installed to $DEFAULT_PREFIX

## Binary Verification

```
$ $DEFAULT_PREFIX/bin/mac
--- Monkey's Audio Console Front End (v 12.60) Copyright 2000-2026 Matthew T. Ashland ---
Proper Usage: [EXE] [Input File] [Output File] [Mode]
...
```

## Staging Verification

- bin/mac: ELF shared object, 64-bit LSB arm64, dynamic (PIE)
- lib/libMAC.so: shared library with NEON SIMD optimization
- include/MAC/*.h: 11 header files

## Conan Verify Results

| Gate | Result |
|------|--------|
| G0 (pre-build assessment) | ✅ PASS |
| G1 (recipe completeness) | ✅ PASS |
| G2 (conan create) | ✅ PASS |
| G3 (system-lib collision R26) | ✅ PASS |
| G4 (artifact integrity) | ✅ PASS |
| L2 (smoke test) | ✅ PASS |
| L4 (security scan) | ✅ PASS |
| L5 (baseline) | ✅ PASS |

## Conclusion

All tests passed. Binary runs correctly on OpenHarmony aarch64.
