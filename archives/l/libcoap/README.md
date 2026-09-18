# libcoap

libcoap is a C implementation of the Constrained Application Protocol (RFC 7252),
with DTLS (OpenSSL), TCP/TLS, WebSockets and OSCORE support.

## OHOS adaptation

### 4.3.5b

- Builds with CMake (`DTLS_BACKEND=openssl`, docs off, tests and examples on).
- Depends on Conan `openssl` for DTLS and `cunit` for the upstream `testdriver` suite.
- Keeps the upstream `coap-3` shared library ABI and installs the
  `coap-client` / `coap-server` / `coap-rd` example binaries.
- Runs the upstream CUnit `testdriver` during the build and a 5-check
  consumer test (`test_coap`) in `test_package`.

### 4.3.4

- CMake 工程，静态库 `coap-3`（不启用 DTLS/TLS 后端，保持上游默认关闭；examples 与 doxygen 关闭）。
- 上游测试：`ENABLE_TESTS=ON` 构建 CUnit `testdriver`，配方 `build()` 内真实执行并以 CUnit 汇总判定。
- `test_package` 的 `test_libcoap` 以消费者身份编译链接并做 PDU 回环 + 断言。

## Dependencies

- `cunit/2.1.3` (upstream tests)
- `openssl/3.5.6.1` (DTLS backend, 4.3.5b only)

## References

- https://libcoap.net/
- https://github.com/obgm/libcoap
