# actor-framework 0.17.6 adaptation notes

The package builds the upstream core and I/O modules as static libraries by
default. OpenSSL, OpenCL, Python bindings, examples, and tools are optional
upstream features and are disabled for this base package, so it has no external
Conan dependencies.

CAF 0.17.6 relied on transitive standard-library includes that are no longer
provided by modern GCC and Clang. The portability patch adds only the headers
used directly by three upstream headers:

- `<cstddef>` and `<cstdint>` for `atom_val.hpp`;
- `<cstdint>` for `ripemd_160.hpp`;
- `<iterator>` and `<limits>` for `receive_buffer.hpp`.

No implementation or upstream test was changed. With core and I/O enabled,
the upstream CMake project registers 112 CTest cases: 100 core cases and 12 I/O
cases. The Conan build runs all 112 tests on native Linux. Cross builds compile
the libraries for OHOS but do not pretend to execute aarch64 tests on the
Windows build host.

The added consumer creates a real actor system, sends a request and validates
the reply. Its fault-injection mode sends a negative value and verifies that
CAF propagates `sec::invalid_argument` through the request/reply channel.
