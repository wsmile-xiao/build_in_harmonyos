# KContacts

KContacts is the KDE Frameworks 6 contacts/address book library. It provides
KF6Contacts (`KF6::Contacts`: the vCard addressee and contact-group model,
address/geography/phone types and import/export helpers) that Akonadi
contact-related libraries and PIM applications build on.

Two versions are archived side by side: 6.18.0 (KF6 6.18 family baseline) and
6.14.0 (KF6 6.14 family alignment for consumers that exact-pin 6.14, e.g.
mauikit/4.0.2 and kio/6.14.0); each has its own OHOS adaptation section below.

## OHOS adaptation (shared)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist (OHOS is
  not in the upstream list).
- `USE_QML=OFF` keeps the package focused on the contact library needed by the
  Akonadi chain; `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.
- `ki18n_install(po)` is disabled by patch 0001 because the Qt Linguist tools
  component is not part of the qtbase package used here; the same patch
  applies to both versions.
- CMake has no `Platform/HarmonyOS` module, so the recipe sets
  `cmake_system_name=OHOS` plus a `CMAKE_USER_MAKE_RULES_OVERRIDE` defining
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`
  (`knowledge/drafts/DRAFT-cmake-harmonyos-platform-soname-flag.md`). Without
  it `libKF6Contacts` has no `DT_SONAME` and consumers bake absolute
  conan-cache paths into `DT_NEEDED`, which musl cannot re-resolve on another
  machine.
- Installed package ELF files are re-signed after `cmake --install` for the
  OHOS runtime loader; runtime verification symlinks dependency `.so*` files
  instead of copying them to preserve code signatures.
- Host tools (cmake/lld) get the OHOS SDK `llvm/lib` prepended to
  `LD_LIBRARY_PATH` only for host execution so SDK `lld` can load its
  `libxml2.so.16`; that path never leaks into CTest target execution.

## OHOS adaptation (6.18.0)

- KF6 6.18 dependency family (`kcodecs`/`kconfig`/`kcoreaddons`/`ki18n`
  6.18.0).
- Upstream CTest 30/30 runnable entries passed (runner
  `codex-a-kcontacts-kcontacts-6.18.0-r2-20260827-204232-31359`); the two
  address tests are excluded because the iso-codes geographic data surface is
  absent from the OHOS device image (environment limitation,
  `knowledge/drafts/DRAFT-kde-pim-testdata-iso-codes-tzdata.md`).

## OHOS adaptation (6.14.0)

- KF6 6.14 dependency family (`kcodecs`/`kconfig`/`kcoreaddons`/`ki18n`
  6.14.0); `qtbase/6.11.1`, `ecm/6.26.0` and `shared-mime-info/2.5.1` are
  shared with the 6.18.0 recipe.
- Same single patch 0001 applies unchanged (context matches verbatim, pure
  line offset).
- The test_package adds an OHOS-specific check (`test_ohos_soname.cpp`) that
  the consumer executable references `libKF6Contacts.so.6` through the SONAME
  (relative `DT_NEEDED`, no slash-qualified absolute path) — the property the
  recipe-layer SONAME override exists to guarantee — and that `__OHOS__` is
  actually defined by the toolchain triplet.
- Status: verified by authoritative device CI — upstream CTest 30/30 runnable
  entries passed, test_package 2/2 (runner and package reference in
  `manifest.yaml`).
