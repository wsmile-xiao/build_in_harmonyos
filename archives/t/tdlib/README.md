# tdlib

TDLib (Telegram Database library) — the cross-platform client library for Telegram.
Ships the JSON/C client API (`libtdjson.so`, `td/telegram/td_json_client.h`), the static
`tdclient`/`tdcore`/`tdapi`/`tdutils`/`tdactor`/`tdnet`/`tddb` toolchain, and the upstream
`Td` CMake package (`Td::TdJson`, `Td::TdJsonStatic`, `Td::TdStatic`).

## Homepage
https://github.com/tdlib/td

## License
BSL-1.0 (Boost Software License 1.0)

## Build System
CMake (upstream `CMakeLists.txt`, `project(TDLib VERSION … LANGUAGES CXX C)`)

## Dependencies
- OpenSSL — mandatory; upstream aborts with "Can't find OpenSSL: stop TDLib building"
- zlib — mandatory; upstream aborts with "Can't find zlib: stop TDLib building"
- gperf / CMake — build-only (gperf is skipped entirely when cross-compiling)
- PHP, ccache, Readline, JNI, crc32c, abseil — upstream-optional, not enabled

## OHOS Adaptation
- CMake 4.x rejects `cmake_minimum_required(VERSION 3.0.2)`; `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
  is passed on the configure command line (cannot go into the Conan toolchain file — CMake loads
  it only at the first `project()`, after CMakeLists.txt:1 has been evaluated)
- The Conan profile pins `compiler.cppstd=17` while upstream appends `-std=c++14`; CMake places the
  CMAKE_CXX_STANDARD flag last, so the build is C++17 and the gperf-generated MIME tables
  (`register` keyword) fail to compile — fixed with `-Wno-register` from the Conan toolchain flags
- tdlib reads OpenSSL through the classic `OPENSSL_FOUND`/`OPENSSL_INCLUDE_DIR`/
  `OPENSSL_CRYPTO_LIBRARY`/`OPENSSL_SSL_LIBRARY` names, which Conan's CMakeDeps never defines
  (it only emits lowercase `openssl_*`); the recipe wires them to the Conan package, which keeps
  OpenSSL statically linked into `libtdjson.so`
- No upstream source is patched (`patches/` is empty)
- OHOS Conan profile leaves `CMAKE_SYSTEM_NAME` unset, so `CMAKE_CROSSCOMPILING=FALSE` and the
  upstream `test/` suite is built and runs natively on device

## Versions
- 1.8.0 — built 2026-09-24 (upstream `run_all_tests` 208/208 on device, `test-tdutils` 109/109,
  `test-crypto` exit 0; `test-online` needs Telegram api-id/api-hash and is not runnable here)
