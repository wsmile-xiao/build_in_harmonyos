Tested on HarmonyOS PC (OHOS 6.0, aarch64) with conan 2.29.1 + clang 15.

## Upstream

- Name: ulfius (packaged as libulfius, matching the upstream pkg-config
  name `libulfius` used by the CMake/CPack artifacts)
- Version: 2.7.15
- Tag: `v2.7.15`
- URL: https://github.com/babelouest/ulfius
- License: LGPL-2.1-or-later (LICENSE file)

## Build system

CMake 3.5+ upstream, C99. Upstream CMake options:

- WITH_GNUTLS (default ON) — websocket TLS backing
- WITH_WEBSOCKET (default ON, depends on WITH_GNUTLS + non-Windows) —
  enabled: gnutls/3.8.10 + zlib/1.3.1 available on ohpcd
- WITH_WEBSOCKET_MESSAGE_LIST (default ON)
- WITH_CURL (default ON) — client requests / SMTP helpers (curl/8.15.0)
- WITH_JANSSON (default ON), WITH_YDER (default ON)
- BUILD_UWSC (default ON with websocket) — **OFF** in this recipe: uwsc is
  an auxiliary websocket client CLI (tools/); the library websocket
  functionality itself is fully retained and covered by the upstream
  websocket test suite
- BUILD_ULFIUS_TESTING (default OFF; needs Check + Subunit — Subunit
  relaxed by the portability patch, ohpcd libcheck is self-contained)
- BUILD_ULFIUS_DOCUMENTATION / BUILD_RPM / INSTALL_HEADER

This recipe produces the static archive (BUILD_STATIC=ON) that downstream
consumers link directly, same as orcania/libyder/libhoel in this repo.

## OHOS platform notes

1. **CMakeDeps target case mismatch**: upstream links `GnuTLS::GnuTLS`,
   `MHD::MHD`, `Jansson::Jansson` from its bundled find-modules; the conan
   CMakeDeps exports `gnutls::gnutls`, `libmicrohttpd::libmicrohttpd`,
   `jansson::jansson` (lowercase, with the complete static transitive
   closures). The portability patch makes every dependency lookup prefer
   the CMakeDeps target when present and fall back to the bundled
   find-module otherwise (the fallback path is seedable through the
   recipe for MODULE mode).
2. **Static transitive closures**: gnutls::gnutls carries nettle,
   libtasn1, libgcrypt, libgpg-error, gmp, libunistring; CURL::libcurl
   carries openssl/3.5.6.1 + zlib/1.3.1. Linking the CMakeDeps targets
   (instead of UNKNOWN IMPORTED bare libraries) resolves the whole chain
   at link time.
3. **No certtool on OHOS**: the upstream framework/websocket TLS test
   cases load cert/server.crt, cert/root1.crt, cert/client1.* ... from
   the test working directory; upstream generates them with
   test/cert/create-cert.sh (gnutls certtool). The recipe executes the
   unmodified upstream script with the certtool binary shipped inside the
   conan gnutls/3.8.10 package (PATH + LD_LIBRARY_PATH injection).
4. **Loopback networking**: the framework tests start real ulfius
   instances on 127.0.0.1 loopback ports and drive them with
   ulfius_send_http_request (curl-backed); the SMTP cases build their own
   socket server on localhost with pthreads. No external network is
   required; OHOS loopback works out of the box.
5. **rt library**: upstream appends `rt` to TEST_LIBS on non-Apple
   non-Windows. OHOS musl provides rt stubs; the link works unmodified.

## Runtime vs. test-build dependencies

- **Runtime**: orcania (allocators), libyder (logging), jansson (json
  bodies), libmicrohttpd (HTTP engine), gnutls (websocket TLS), zlib
  (permessage-deflate), curl (client requests / SMTP). All published on
  ohpcd (W0 verified with conan download).
- **Test-build stage**: the unmodified upstream check suites need the
  Check framework. The recipe pulls check/0.15.2 from ohpcd as a
  **test-only** (test_requires) dependency — same pattern as orcania
  2.3.3 / libyder 1.4.20 / libhoel 1.4.29.

## Why upstream tests are enabled (rule 4)

Upstream v2.7.15 ships five CTest test programs (test/core.c,
test/u_map.c, test/framework.c, test/example_callbacks.c,
test/websocket.c — 13 + 9 + 28 + 25 + 13 = 88 START_TEST cases) built
with BUILD_ULFIUS_TESTING=ON. They are registered as EXCLUDE_FROM_ALL and
executed here inside `conan create` (via ctest), so the official tests
genuinely pass 88/88 on OHOS aarch64 (websocket included).

Case list (all pass) — core: 13 (instance init/clean, endpoint add,
request/response structures, u_map bindings); u_map: 9 (map get/set/
enum/remove cases); framework: 28 (endpoint callbacks incl. stream,
multiple handlers, injection, SMTP round trip on a pthread socket
server, large posts, post processor, send_http_request against a live
loopback instance, TLS server-ca-trust and client-certificate with the
certtool-generated certs); example_callbacks: 25 (http_compression,
static_compressed_inmemory_website callbacks); websocket: 13 (client
connections, extensions incl. permessage-deflate, keep_messages, origin,
json messages).

## Patches

`0001-ohos-portability.patch` (portability, CMakeLists.txt only):

1. GnuTLS/MHD/Jansson/ZLIB/CURL lookups prefer the Conan CMakeDeps
   targets (gnutls::gnutls, libmicrohttpd::libmicrohttpd,
   jansson::jansson, zlib::zlib, CURL::libcurl) which carry the complete
   static transitive link closures; fall back to the upstream bundled
   find-modules (MODULE mode) otherwise.
2. Orcania/Yder version gates accept the camel-case VERSION_STRING that
   Conan CMakeDeps exports (gate still enforced through the
   *ConfigVersion.cmake files).
3. Under BUILD_STATIC=ON the conan package only exports the *-static
   targets, so the unconditionally built shared target must link them
   too or the bare names resolve to nothing and the compile loses the
   include dirs.
4. Test tree: force find_package(Check MODULE) so the bundled
   FindCheck.cmake runs under CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON;
   relax the Subunit hard requirement (ohpcd libcheck is
   self-contained); link the tests against the actual library target
   (ulfius_static) under BUILD_STATIC.

Upstream test sources (test/*.c) are untouched.
