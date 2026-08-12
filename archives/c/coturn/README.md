# coturn

Coturn provides a TURN/STUN server and protocol utilities for NAT traversal.

## OpenHarmony Scope

The recipe builds the server and installed TURN/STUN utilities with external
libevent, OpenSSL, and SQLite dependencies. Its `build()` method enables the
upstream CMake test suite and invokes `ctest --output-on-failure`.

The packaged consumer test runs `turnutils_rfc5769check`, which validates the
published RFC 5769 STUN test vectors. It supplements rather than replaces the
upstream suite.

## Validation Status

No upstream test result is claimed in this archive until the OpenHarmony CI
run completes. Optional database-driver cases remain controlled by upstream
feature detection and are not removed by the recipe.
