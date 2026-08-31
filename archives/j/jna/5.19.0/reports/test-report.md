# Test Report — jna 5.19.0

## Build Verification
- **Build system**: Custom (clang + libffi static link)
- **Compiler**: clang 15.0.4
- **Platform**: HarmonyOS aarch64
- **Status**: SUCCESS

## Build Artifacts
| Artifact | Size | Dependencies |
|----------|------|-------------|
| libjnidispatch.so | 182KB | libc.so only (libffi static linked) |
| libtestlib.so | 34KB | libc.so, libdl.so |
| libtestlib2.so | 18KB | libc.so, libdl.so, libtestlib.so |

## Conan Verification (conan-verify)
| Gate | Result |
|------|--------|
| G1: Recipe completeness | PASS |
| G2: conan create (clean build) | PASS |
| G3: System lib isolation (R26) | PASS |
| G4: Artifact completeness | PASS |
| L2: Smoke test | PASS |
| L4: Security scan | PASS |
| L5: Artifact baseline | PASS |

## W3 Local CI Simulation
- setup.sh: PASS
- build_and_test.sh: PASS

## Test Package
- **Test**: dlopen + dlsym smoke test for JNI exports
- **Symbols verified**: 10 JNI functions
- **Result**: PASS

## Dependency
- libffi/3.4.4 (conan repo, static linked)
