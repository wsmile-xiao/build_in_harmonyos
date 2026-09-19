# kfourinline 26.04.0 notes

## Scope

KDE four-in-a-row game (KWin4): the kfourinline GUI application plus the
kfourinlineproc computer-player AI engine process, both built on the
published libkdegames 26.04.0 (KDEGames6/KDEGames6Private, platform task
#12820; the libkdegames dependency chain landed via #9978).

## Upstream shape (26.04.0 tarball)

- Qt6 6.5+/KF6 6.0+ CMake project (ECM toolchain), Qt6 Svg+Widgets.
- Two executables: `kfourinline` (QApplication GUI, src/) and
  `kfourinlineproc` (QCoreApplication AI process: the game spawns it via
  KProcess and exchanges KGame messages over stdin/stdout, src/kwin4proc.cpp
  + src/kgameprocess.cpp).
- Upstream REQUIRED KF6 set: Config, ConfigWidgets, CoreAddons, Crash,
  DBusAddons, DNSSD, DocTools, I18n, WidgetsAddons, XmlGui, IconThemes
  + KDEGames6 6.0.0.
- No test suite: no tests/, autotests/ or add_test() anywhere (N=0).
- themes/ installs SVGZ theme files (gzip fallback when 7Zip is absent),
  icons/ installs hicolor PNG icons, doc/ builds the DocBook handbook via
  kdoctools_create_handbook.

## Adaptations

- patches/0001-ohos-skip-kdoctools.patch: DocTools removed from the KF6
  REQUIRED list; add_subdirectory(doc) and kdoctools_install(po) dropped.
  kdoctools is not part of the published KF6 6.18/6.26 closure (kdoctools
  6.19.0 exists in the registry but drags karchive/6.19.0 which conflicts
  with the knewstuff 6.18.0 closure pinned by libkdegames 26.04.0); the
  DocBook handbook is not a runtime requirement for the game (audiocd
  26.04.3 / libkcddb 26.04.3 precedent for the same trim).
- KF_IGNORE_PLATFORM_CHECK=TRUE, KF_SKIP_PO_PROCESSING=ON (standard KDE
  OHOS set, libkdegames/khealthcertificate precedent).
- karchive/6.18.0 pinned with override=True (libkdegames 26.04.0 graph
  precedent: newest kiconthemes/6.18.0 revision requires karchive/6.19.0,
  knewstuff/6.18.0 requires karchive/6.18.0).
- Qt6Svg resolved from qtsvg/6.11.1 via QT_ADDITIONAL_PACKAGES_PREFIX_PATH
  (libkdegames verified pattern).
- ECM_MODULE_PATH set manually + conan_cmakedeps_paths.cmake written
  manually (cmake_find_mode=none packages are not added to
  CMAKE_PREFIX_PATH by CMakeDeps).
- -Wl,-z,max-page-size=0x1000 linker pin (OHOS musl loader rejects the
  default lld 0x10000 multi-RW-LOAD layout; audiocd 26.04.3 precedent).
- Host tools (moc/uic/rcc, kconfig_compiler) are OHOS binaries from the
  conan packages: build env prepends /system/lib64 + SDK llvm/lib +
  dependency lib dirs to LD_LIBRARY_PATH (audiocd/kconfig precedent).

## Verification

OHOS `conan create` (local, aarch64, clang, Release) - PASSED:

- 32/32 dependency packages installed (ohpcd registry + local cache).
- Upstream test suite: N=0 (upstream registers none).
- test_package smoke: 2/2 assertions passed -
  - kfourinline --version prints "kfourinline 26.04.0" and exits 0
    (QT_QPA_PLATFORM=offscreen).
  - kfourinlineproc prints its "AI process starts up" stderr banner (ELF
    load + Qt runtime init + KGame process construction) and terminates
    cleanly on SIGTERM (rc=143). Note: the upstream AI process has no
    stdin-EOF exit path by design - EOF floods the KMessageFilePipe cookie
    parser with "Cookie error" logs and the process is normally spawned and
    closed by the game through the KGame message protocol; the smoke test
    therefore verifies startup + clean termination instead of EOF exit.
- package_id: 40c9b7ce2f8cf4da4573c8a93f7833b6195a9d53.

## Local run env notes (test_package)

- Published KF6/Qt6/KDEGames6 binaries embed absolute-path DT_NEEDED
  entries pointing at the building machine's conan cache layout
  (~/.cache/conan2/p/<hash>/p/lib); the OHOS musl loader does not fall
  back to LD_LIBRARY_PATH for absolute-path entries. On this machine the
  referenced paths were provisioned under ~/.cache/conan2 (registry CI
  layout), plus a <build>/../../bin symlink farm for the
  build-tree-relative ("../../bin/lib*.so") entries (libkdegames /
  khealthcertificate precedent).
- Qt platform plugins: QT_QPA_PLATFORM_PLUGIN_PATH/QT_PLUGIN_PATH point at
  the qtbase package plugins dir (offscreen platform for headless smoke).
- The loader vars are persisted via os.environ because conan's self.run()
  spawns a fresh shell (khealthcertificate 26.04.3 precedent).

## Runtime notes

- The game needs KDEGames6 + Qt6/KF6 libs on LD_LIBRARY_PATH (package_info
  exports the dependency lib dirs via runenv_info) and the KDEGames6 QML
  import path for the reflection scene.
- Network games need KDNSSD (mDNS) infrastructure on the target.
