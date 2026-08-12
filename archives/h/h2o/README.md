# h2o

H2O is an optimized HTTP server with HTTP/2 support and embeddable event-loop
libraries.

## OpenHarmony Scope

The recipe consumes Conan-provided libuv, OpenSSL, and zlib. It preserves the
project's upstream `check` target, which includes the selected upstream test
path, instead of substituting a consumer-only smoke test.

MRuby is outside the first package configuration because it needs a Ruby and
Bison host-tool chain. That configuration boundary is documented for review;
it does not convert a skipped MRuby test into a passing test.

## Validation Status

The `h2o -v` consumer check only verifies the packaged binary. No upstream
test result is claimed until the full upstream `check` target has run on an
OpenHarmony PC device and recorded an actual `passed/total` result. Pending CI
and host-native results are not OpenHarmony device validation.
