# libarcus

libArcus is the Ultimaker C++ socket communication library based on Protocol Buffers,
used for communication between Cura and its backend components.

## OHOS adaptation

- CMake build with Python bindings disabled (`BUILD_PYTHON=OFF`), no SIP dependency.
- Depends on `protobuf/3.17.3` from the local registry (upstream requires Protobuf 3.17.1).
- Upstream 5.0.0 ships no automated test suite (audited `no_tests` case); verification
  relies on two consumer tests covering the Socket lifecycle and the Error value class.

## Dependencies

- protobuf 3.17.3 (transitive: zlib 1.3.1)

## References

- Upstream: https://github.com/Ultimaker/libArcus
- Version: 5.0.0 (`https://github.com/Ultimaker/libArcus/archive/refs/tags/5.0.0.tar.gz`)
