# libcoap

libcoap is a C implementation of the Constrained Application Protocol (RFC 7252),
with DTLS (OpenSSL), TCP/TLS, WebSockets and OSCORE support.

## OHOS adaptation

- Builds with CMake (`DTLS_BACKEND=openssl`, docs off, tests and examples on).
- Depends on Conan `openssl` for DTLS and `cunit` for the upstream `testdriver` suite.
- Keeps the upstream `coap-3` shared library ABI and installs the
  `coap-client` / `coap-server` / `coap-rd` example binaries.
- Runs the upstream CUnit `testdriver` during the build and a 5-check
  consumer test (`test_coap`) in `test_package`.

## Dependencies

- `openssl/3.5.6.1` (DTLS backend)
- `cunit/2.1.3` (upstream tests)

## References

- https://libcoap.net/
- https://github.com/obgm/libcoap
