# MathGL 8.0.3-ds.2 HarmonyOS PC verification

Date: 2026-09-29. Claimed task: #8705. Team: 诶，云朵. Candidate path: B, subject to event review.

- The Debian `+ds.2` orig tarball SHA-256 is `951ce522b84627062e28e6a45e0e9f8d1ced04835f271a488d152fece699d1db`. It deliberately omits `src/s_hull`. The matching Debian source tarball SHA-256 `6b00f972103701e600d614fcc3742c3531bb6b13ed13839bf45403de4aaed73c` supplies the two original GPL-3 files, and `debian/rules` copies them before configure. This recipe exports those exact hash-checked files; it does not synthesize replacements. The combined static archive is declared GPL-3-only.
- Published OHOS arm64 zlib 1.3.2 and libpng 1.6.58.3 satisfied the dependency graph without building the dependencies. Optional GUI, SWIG, Python, OpenGL, and MPI integrations are disabled; this is the core static library plus a build-only native test driver.
- The first unique target run stopped during CMake generation on missing `s_hull/s_hull_pro.cpp` and was released as a failure. The final run is `mathgl-w3-20260929T051636Z`, frozen bundle SHA-256 `2c2a7148df553ad3f23afb7b77a9a7eae1e621b0f5c6b5cacda3459e90bd69f1` with exact transfer/readback and a single launch.
- `conan create` returned 0. The upstream `mgl_example --mini --srnd` path rendered and validated 149 PNG samples, and `mgl_example --test --mini` rendered one test PNG: **150/150**. The release has no CTest registrations; the inventory comes from the actual upstream native driver rather than incorrectly reporting 0/0.
- The installed-package `test_package` linked through `mathgl::mathgl`, rendered a PNG, checked its signature, and printed `MATHGL_PNG_OK`: **1/1**.
- Full Conan log SHA-256 is `adf59f18d6c1fc010f9fe32e98ccf4738068a00d9c2525e4fe89e4106472e3d0`. Frozen W3 validator returned `W3_VALIDATOR_PASS`, chain head `cbc546799c92cef29240cb02e847e108b96416c5cdd03be7c691d16e9431f7cd`, including runner absence, release, and postrelease.

The Debian Python-binding autopkgtest is outside this package's enabled feature scope; it is not counted as a passed core-library test. No platform CI, merge, registry publication, or score approval is claimed here.
