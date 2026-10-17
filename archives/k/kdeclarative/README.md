# KDeclarative

KDeclarative is the KDE Frameworks 6 declarative bindings framework: the QML
integration layer providing C++ helpers backing QML components (quickaddons),
the kquickcontrols QML plugin modules (KeySequenceItem, ColorButton, ...),
kquickcontrolsaddons items (QImageItem, QPixmapItem, Clipboard,
MouseEventListener), draganddrop + graphicaleffects QML plugins and the
CalendarEvents C++ library used by calendar data sources.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` (OHOS not in the KDE platform allowlist),
  `KF_SKIP_PO_PROCESSING=ON` (Qt6LinguistTools not published),
  `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON` (kdoctools not published).
- `patches/0001-ohos-disable-kglobalaccel.patch`: the generic Linux branch
  requires KF6GlobalAccel; it is not published in the ohpcd registry and OHOS
  has no desktop global-shortcut registry, so HAVE_KGLOBALACCEL is forced
  FALSE (same no-op semantics as the upstream ANDROID/IOS branches — no stubs,
  the optional accelerator integration compiles out).
- `patches/0002-lower-ecm-and-kf-dep-version.patch`: KF_DEP_VERSION floor
  lowered 6.26.0 -> 6.19.0; the published ohpcd KF6 deps are consumed at
  6.26.0 (>= the floor).
- ECM 6.26 `KDEInstallDirs6` runs the qtbase `qtpaths` host tool during
  configure; `/system/lib64` + SDK llvm lib are prepended to
  `LD_LIBRARY_PATH` so the compatible `libc++_shared.so` wins (kconfig
  6.26.0 / kpackage 6.26.0 precedent).
- QML plugin libraries ship as private QML module plugins dlopen'ed through
  QML2_IMPORT_PATH; `cpp_info.libs` carries KF6CalendarEvents and the qml
  import paths are exported through `runenv_info`.

## Version index

| 版本 | 状态 | 说明 |
|------|------|------|
| 6.26.0 | built | 首次适配 OHOS aarch64（HarmonyOS PC），KF 6.26 基线链 |

## Upstream

- Homepage: https://invent.kde.org/frameworks/kdeclarative
- Source: https://download.kde.org/stable/frameworks/6.26/kdeclarative-6.26.0.tar.xz
