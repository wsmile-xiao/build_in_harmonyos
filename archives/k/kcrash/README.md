# kcrash

KDE Frameworks 6 crash-handling framework (libKF6Crash.so). Supports
catching and processing application crashes, launching the DrKonqi crash
handler, and writing crash metadata.

- Upstream: https://invent.kde.org/frameworks/kcrash
- License: LGPL-2.0-or-later
- Build system: CMake (ECM / KDEInstallDirs)

## Adapted versions for HarmonyOS PC (aarch64)

| Version | Status | Notes |
|---------|--------|-------|
| 6.14.0  | built  | Initial KF6 baseline |
| 6.18.0  | built  | Akonadi KF baseline refresh |
| 6.26.0  | built  | KF6 6.26 baseline chain (task #6328): qtbase 6.11.1 + kcoreaddons 6.26.0 + ecm 6.26.0 |

## OHOS adaptation notes (all versions)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist.
- `BUILD_DESIGNERPLUGIN=OFF` (Qt6UiPlugin not published to ohpcd).
- `WITH_X11=OFF` (OHOS has no X11; upstream defaults it ON for the
  UNIX-non-Apple-non-Android-non-Haiku branch that HarmonyOS matches).
- `BUILD_TESTING=ON` runs the upstream CTest autotests inside conan create.
- Library package: no bin/ artifacts, no commands.json needed.
