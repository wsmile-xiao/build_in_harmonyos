# libmacaroons

Macaroons are flexible authorization credentials supporting decentralized
delegation, attenuation, and verification.

## OHOS adaptation

- Builds the official `releases/0.3.0` tarball with its pre-generated
  Autotools files (no `autoreconf` on device).
- Upstream `configure` hard-errors when `libbsd` is absent. OHOS has no
  `libbsd` conan package, so the recipe softens that check to a warning
  and links against libc (musl provides the needed symbols on device;
  see `notes.md` for the evidence chain).
- Upstream tests are automake `TESTS` executed via `make check`
  (`test/varint` plus the `test/unit/*.vtest.sh` stubs driving
  `macaroon-test-verifier` / `macaroon-test-serialization`).
- Installed-package consumer (`test_package/`) creates a macaroon, adds a
  first-party caveat, and verifies it through the real C API.

## Dependencies

None (libc only after the libbsd bypass).

## References

- https://github.com/rescrv/libmacaroons
- https://github.com/rescrv/libmacaroons/archive/releases/0.3.0.tar.gz
