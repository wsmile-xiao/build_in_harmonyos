# kglobalaccel

KDE Frameworks 6 global-shortcut framework (libKF6GlobalAccel.so). Provides
application-global keyboard shortcuts that work independently of the focused
window, plus the `KDED`-side registration interface over D-Bus.

- Upstream: https://invent.kde.org/frameworks/kglobalaccel
- License: LGPL-2.0-or-later
- Build system: CMake (ECM / KDEInstallDirs)
- Tier: 1 (`type: integration`, `cmakename: KF6GlobalAccel`)

## Adapted versions for HarmonyOS PC (aarch64)

| Version | Status | Notes |
|---------|--------|-------|
| 6.26.0  | built  | First HarmonyOS PC adaptation: qtbase-sql-dbus 6.11.1 (Qt6::DBus) + qt6linguisttools 6.11.1 (poqm) + qtdeclarative 6.11.1 (tests) + ecm 6.26.0 |

## OHOS adaptation notes

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (metainfo.yaml lists Linux/FreeBSD only; ECM aborts configure on
  HarmonyOS otherwise).
- `WITH_X11=OFF` disables the X11 code path: upstream defaults it ON and
  `src/kglobalaccel.cpp` then includes `<private/qtx11extras_p.h>`, which the
  OHOS qtbase / qtbase-sql-dbus builds do not ship (FEATURE_xcb/xlib=OFF).
- `Qt6::DBus` is provided by `qtbase-sql-dbus/6.11.1`; `qtbase/6.11.1` is
  built with `FEATURE_dbus=OFF` and ships no `Qt6DBus` cmake module.
- `qt6linguisttools/6.11.1` supplies `Qt6::LinguistTools` (lrelease), which
  `ecm_install_po_files_as_qm(poqm)` requires (102 translation catalogs).
  Qt's split-module packages are announced through
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`.
- `qtdeclarative/6.11.1` supplies `Qt6::Qml` for the upstream tests target.
- No source patches are applied — the recipe layer alone is enough.
- Library package: no bin/ artifacts, no commands.json needed (R38).
