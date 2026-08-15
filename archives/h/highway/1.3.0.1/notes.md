# Highway 1.3.0.1 verification notes

## Upstream test mode

The default package keeps the first-pass library build compact. Set
`-o highway/*:with_upstream_tests=True` to enable `BUILD_TESTING`, Highway's
upstream and contrib test targets, and `HWY_TEST_STANDALONE`.

Standalone mode uses Highway's built-in GTest-compatible command-line runner,
so CMake can discover and execute the upstream tests without downloading or
linking GoogleTest. This note records the intended test configuration only; it
does not report a host, CI, or HarmonyOS PC test result for this package head.
