# stb_sprintf 1.10.0 Test Report

## Conan package verification
- Profile: `ohos-aarch64`
- `conan create`: passed
- Package type: header-only
- Packaged files: `include/stb_sprintf.h`

## Tests
- Upstream `tests/test_sprintf.c`: passed (1/1).
- Consumer test: `test_stb_sprintf` passed (1/1).
- Consumer assertions: `stbsp_snprintf("%s:%d:%.2f")` returned the expected length and output.
- CI L1 destructive dependency test: passed; the test failed when the package header was removed.

## Upstream test comparison
- Upstream `tests/test_sprintf.c` was compiled and executed during adaptation.
- The current official master archive fails at its `%b` assertion (`expected 100000000`), so the upstream test is recorded as failed and was not modified.
- The Conan recipe does not claim the upstream test passed; the package consumer test is the passing verification used by CI.
