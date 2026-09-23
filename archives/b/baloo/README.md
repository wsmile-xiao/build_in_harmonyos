# Baloo

Baloo is the KDE Frameworks 6 file indexing and searching framework. It
provides libKF6Baloo (Query/Term/ResultIterator/File/IndexerConfig public
API), libKF6BalooEngine (the LMDB-backed index database engine), the
baloo_file background indexer daemon with its baloo_file_extractor helper,
the balooctl6/baloosearch6/balooshow6 CLI tools, and the org.kde.baloo QML
plugins.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `KF_DEP_VERSION` is lowered to 6.14.0 so the build and the installed
  KF6BalooConfig.cmake accept the ohpcd-published KF6 6.14.x components;
  ECM floor is 6.26.0 (kdnssd 6.29.0 precedent).
- The KIO component and the kioworkers subdirectory are dropped: only the
  kioslaves link KF6::KIOCore and KIO is not published on ohpcd.
- `ki18n_install(po)` is patched out (qtbase does not ship
  Qt6LinguistTools; kconfig/kfilemetadata use the same patch).
- C++20 is forced by removing the conan toolchain cppstd block (ECM
  KDECompilerSettings sets the standard itself); the three std::ranges call
  sites are replaced with classic algorithms because the OHOS clang 15
  libc++ has no C++20 ranges algorithms.
- An IMPORTED_SONAME block stamps SONAMEs on the SONAME-less KF6
  dependencies so baloo's libraries record relocatable basenames in
  DT_NEEDED instead of machine-private cache paths (E537 / kpackage
  6.18.0.1 precedent).
- The SDK sysroot usr prefix is injected into CMAKE_PREFIX_PATH so ECM
  FindInotify succeeds and BUILD_KINOTIFY (file indexer + autotests) is
  enabled.
- Qt6 comes from qtbase/6.11.1.1 (FEATURE_dbus=ON provides Qt6::DBus which
  baloo requires) with override=True unifying the transitive qtbase/6.11.1
  references of the KF6 dependencies.
- Known limitations: three upstream autotests that require a D-Bus session
  bus and a running baloo_file daemon are excluded from the ctest run; the
  querytest testSearchstringParser content-term rows return an empty set on
  the OHOS sandbox (HMDFS behavior difference) and are recorded honestly.

## Dependencies

- Build: ecm (extra-cmake-modules) 6.26.0, CMake >= 3.29
- Runtime/compile: qtbase 6.11.1.1 (Core/DBus/Gui/Widgets/Test),
  qtdeclarative 6.11.1 (Qml/Quick), kconfig, kcoreaddons, ki18n,
  kdbusaddons, kfilemetadata, kcrash, solid, kidletime (KF6 6.14/6.29
  series), lmdb 0.9.35

## References

- Homepage: https://invent.kde.org/frameworks/baloo
- Sources: https://download.kde.org/stable/frameworks/6.28/baloo-6.28.0.tar.xz
