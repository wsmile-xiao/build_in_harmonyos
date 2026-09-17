# lib1305

lib1305 is a microlibrary for the Poly1305 one-time authenticator
(D. J. Bernstein), intended to be called by larger cryptographic libraries
via a small SUPERCOP-style API.

## OHOS adaptation

- Custom djb build system (`./configure` python script + `Makefile`);
  toolchain is injected through the first line of `compilers/default`
  (same mechanism as the libcpucycles adaptation).
- `librandombytes` has no HarmonyOS package in this repository yet; the
  recipe carries a minimal build-time-only shim (`vendor-randombytes/`)
  that satisfies upstream's unconditional `-lrandombytes` link lines.
  The library itself never calls `randombytes`, so consumers gain no
  extra dependency.
- Upstream's conventional test suite (`lib1305-test`) runs inside the
  recipe `build()`; the `test_package` consumer test checks the public
  API against the RFC 8439 section 2.5.2 known-answer vector.

## Dependencies

- `libcpucycles/20260625` (build-time only, for the `lib1305-speed`
  benchmark tool; not shipped, not required by consumers)

## References

- https://lib1305.cr.yp.to
- https://lib1305.cr.yp.to/api.html
- https://lib1305.cr.yp.to/test.html
