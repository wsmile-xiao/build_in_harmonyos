# Vendored upstream tests

The files under `tests/` and `tinytest/` are byte-for-byte copies from the
official libconfig 1.7.3 release archive:

- URL: https://github.com/hyperrealm/libconfig/releases/download/v1.7.3/libconfig-1.7.3.tar.gz
- SHA256: `545166d6cac037744381d1e9cc5a5405094e7bfad16a411699bcff40bbb31ee7`

Pinned file checksums:

- `tests/tests.c`: `e89204a95c4785b79f303a0ea1b37aa2afdb413d25f71240fdabefb4c14a5918`
- `tinytest/tinytest.c`: `a866ca6093970be8686b13e6790915acbade45bc1a85e2cb7644afdaac9483bf`
- `tinytest/tinytest.h`: `ebdf035923079c7cb30f2c244eb95140fffc439cd1a583460b64165e0820d817`

No test source, test data, assertion, or expected output has been modified.
The directories are vendored only because the HarmonyOS CI worker does not
provide `curl`/`wget`, and direct GitHub release downloads are not reliable
from that environment. `test_package/conanfile.py` compiles these tests
against the installed `libconfig.a` and runs them from `tests/`, so relative
`testdata` paths remain identical to upstream.
