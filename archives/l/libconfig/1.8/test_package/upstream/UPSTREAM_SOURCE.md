# Vendored upstream tests

The files under `tests/` and `tinytest/` are byte-for-byte copies from the
official libconfig v1.8 git tag archive:

- URL: https://github.com/hyperrealm/libconfig/archive/refs/tags/v1.8.tar.gz
- SHA256: `22e13253e652ec583ba0dd5b474bd9c7bd85dc724f2deb0d76a6299c421358ef`

(The v1.8 GitHub release ships no tarball asset; the git tag archive is the
canonical upstream dist artifact.)

Pinned file checksums:

- `tests/tests.c`: `169cd16adc67ec867b641929cb39799737550fb7569efd6fbfa5a7bdb1adb8fc`
- `tinytest/tinytest.c`: `4df58a26ee0c50492f4c3f736a3eebd4b20e65b7525b893841e54af8b9d9dda4`
- `tinytest/tinytest.h`: `ca51dca3b66deb317059bd963bb90e68a728d8da0e6f88cd35aa6a92c2108f75`

No test source, test data, assertion, or expected output has been modified.
The directories are vendored only because the HarmonyOS CI worker does not
provide `curl`/`wget`, and direct GitHub downloads are not reliable from that
environment. `test_package/conanfile.py` compiles these tests against the
installed `libconfig.a` and runs them from `upstream/tests/`, so relative
`testdata` paths remain identical to upstream.
