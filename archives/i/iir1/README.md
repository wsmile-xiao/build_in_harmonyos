# iir1

iir1 is a realtime C++ IIR filter library implementing Butterworth,
Chebyshev I/II, RBJ, and custom second-order-section filters.

- Upstream: https://github.com/berndporr/iir1
- License: MIT
- Build system: CMake
- Third-party dependencies: none
- Consumer interfaces: `find_package(iir)`, `iir::iir`, and pkg-config `iir`

## 1.10.0

The OpenHarmony recipe supports shared and static packages, builds all eight
upstream CTest executables, and supplies 46 independently runnable consumer
API tests. See the version directory for exact source hashes and validation
evidence.
