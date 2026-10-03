# kunifiedpush 26.04.0 notes

## Scope

This package is part of the KDE Gear 26.04.0 baseline (task #12932,
integration competition entry). kunifiedpush is the KDE UnifiedPush
integration framework; upstream ships it as a single tarball from the
KDE release-service with cmake + ECM + Qt6/KF6.

The ohpcd package builds the **application client connector library**
(`libKUnifiedPush.so`) only, via the upstream `KUNIFIEDPUSH_CLIENT_ONLY`
option.

## Upstream deliverables vs. shipped scope (W0 dependency verification)

Upstream desktop build has four deliverables:

| Deliverable | Needs | In ohpcd registry | Shipped |
|---|---|---|---|
| libKUnifiedPush.so (client) | Qt6 Core/Test/DBus, OpenSSL::Crypto | yes (qtbase-sql-dbus/6.11.1, openssl/3.5.6.1) | **yes** |
| libKUnifiedPushDistributor.so | + Qt6::WebSockets | qtwebsockets/6.11.1 present but KF6 Solid absent | no |
| libKUnifiedPushNotifier.so | + Qt6::WebSockets, KF6 I18n | same | no |
| kcm_kunifiedpush + management tool | KF6 I18n/Solid/Service/KCMUtils/Crash | solid absent | no |

`KUNIFIEDPUSH_CLIENT_ONLY=ON` is the upstream-supported way to restrict the
build to the client library: it skips the distributor/notifier/KCM/tools
subdirectories and the associated `find_package(Qt6 WebSockets)` +
`find_package(KF6 ...)` requirements (see CMakeLists.txt). The client library
keeps a hard Qt6::DBus dependency on non-Android platforms (DBus adaptor and
interface code generated from `src/interfaces/*.xml` by `qt_add_dbus_adaptor`
/ `qt_add_dbus_interface`).

Registry notes from the W0 pass:

- `qtbase/6.11.1` (used by the KF6 6.26 baseline) is a **reduced-surface**
  package: `FEATURE_dbus=OFF`, `FEATURE_openssl=OFF`, testlib off — it
  cannot satisfy kunifiedpush.
- `qtbase-sql-dbus/6.11.1` (akonadi 25.12.3 / alligator 26.04.0 precedent)
  builds Qt6 Core/Network/Gui/Widgets/Xml/Sql/**DBus**/**Test** and ships
  the `qdbusxml2cpp` host tool plus `lib/cmake/Qt6DBus` with
  `Qt6DBusMacros.cmake` — this is the Qt base for this package.
- `openssl/3.5.6.1` matches the akonadi pinning; the tarball code uses
  OpenSSL for RFC 8291 push content encryption (EC P-256 + AES-GCM) and is
  built with `OPENSSL_API_COMPAT=30000`.
- `ecm/6.26.0` provides KDEInstallDirs/KDECMakeSettings/KDECompilerSettings/
  ECMAddTests/ECMGenerateHeaders/ECMQtDeclareLoggingCategory/ECMSetupVersion/
  ECMDeprecationSettings.

## Adaptations

- `KUNIFIEDPUSH_CLIENT_ONLY=ON`: client library only (see table above).
- `KF_IGNORE_PLATFORM_CHECK=TRUE`: bypass the KDE platform allowlist for
  OHOS (kcrash 6.26.0 precedent).
- `BUILD_TESTING=ON`: builds and runs the upstream autotests available in
  the client-only feature set.
- `ECM_MODULE_PATH` set manually (CMakeDeps-generated ECMConfig.cmake does
  not propagate it; kcrash 6.26.0 precedent).
- `conan_cmakedeps_paths.cmake` written manually (qtbase-sql-dbus uses
  `cmake_find_mode=none`; kcrash 6.26.0 precedent).
- `/system/lib64` prepended to LD_LIBRARY_PATH during configure/build/test:
  the sandbox carries an incompatible `libc++_shared.so` shadowing the
  compatible one (kconfig 6.26.0 / kcrash 6.26.0 precedent).
- No source patch required: the client-only path builds with the plain
  upstream tarball; C++20 is satisfied by the toolchain default from the
  profile (clang 15, libc++, cppstd 17 baseline with the project's own
  `CMAKE_CXX_STANDARD 20`).

## Upstream tests

Upstream `autotests/CMakeLists.txt` registers, in the client-only feature
set (`KUNIFIEDPUSH_CLIENT_ONLY=ON`, non-Android):

- `connectorutilstest` — `ConnectorUtils::selectDistributor` sort/priority
  logic (runs a real `Connector` over the session bus; needs writable XDG
  config for the QSettings state file).
- `contentencryptiontest` — RFC 8291 content decryption vectors (5 test
  slots: testDecrypt, testEmpty, testInvalidMessage, testInvalidKey,
  testKeyGen) linking `KUnifiedPush` + `Qt6::Test` + `Qt6::DBus`.

The remaining autotests (`connectortest`, `serversenteventsstreamtest`,
`contentencryptortest`, `vapidtest`, disabled `ntfytest`) and the `tests/`
demo binaries link the distributor/notifier libraries and are excluded by
the client-only option. The executed upstream CTest count is 2.

## Verification

Initial local checks:

- Upstream tarball HTTP 200 verified against
  https://download.kde.org/stable/release-service/26.04.0/src/kunifiedpush-26.04.0.tar.xz
- Upstream source SHA256 verified:
  `0756dfc94de2bc065542e5c1e366dec2226615bfecc2993381a45051b1c24f03`.

OHOS `conan create` verification passed on 2026-10-01:

- Command: `conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2`
- Runner log: `reports/conan-create.log`.
- Full package reference:
  `kunifiedpush/26.04.0#8f36382d6d1353a5a50a7cf41b200117:4e974afdcfff02f7afe621f2325ad52a59453305`.
- Upstream CTest passed 2/2: `connectorutilstest` (0.07s), `contentencryptiontest`
  (0.11s, 5 test slots) — run inside conan create with BUILD_TESTING=ON.
- Conan `test_package` passed 1/1 with a `KUnifiedPush::Connector` consumer
  compile/link/runtime smoke (empty-service-name construction so the
  bus-dependent distributor discovery is skipped on a bus-less host, then
  state/endpoint checks plus a VAPID public-key property round-trip).

---

**编译结束**: 2026-10-01
**最终状态**: built
