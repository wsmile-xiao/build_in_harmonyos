# Qt5 WebSockets

Qt WebSockets module for Qt5 5.15.2, providing `QtWebSockets` (RFC 6455
WebSocket client/server for Qt applications).

## Build Notes
- Requires: qt5-qtbase/5.15.2.2
- Platform: HarmonyOS (aarch64)
- Build system: qmake
- No source modifications required for HarmonyOS (`patches_applied` is empty)
- `make install` uses `STRIP=true`: qmake's `strip --strip-unneeded` breaks the
  dynamic symbol table and makes `dlopen` fail on HarmonyOS
- Packaged `.prl`/`.la`/`.pc` files are rewritten to remove stale build-dir paths
- Packaged ELF shared objects are signed with `binary-sign-tool -selfSign 1`

## Upstream Tests
The upstream auto test suite (`tests/auto/websockets`, 9 QTest suites /
7322 data cases) is built and executed inside the recipe `build()` step on
the 127.0.0.1 loopback (private_tests feature flipped on in the private Qt
prefix, tst_* binaries signed before execution, results parsed from the
check log and enforced against an environment-limited allowlist).

See `5.15.2/notes.md` for the full per-suite results and the single
environment-limited failure (tst_errorString — fake-IP DNS in the build
environment).

## Consuming
- CMake: `find_package(Qt5WebSockets CONFIG REQUIRED)` → `Qt5::WebSockets`
- qmake: `QT += websockets`
- pkg-config: `Qt5WebSockets`
