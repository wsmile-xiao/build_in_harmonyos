#!/usr/bin/env python3
"""Conan recipe for ktuberling 26.04.0 on HarmonyOS PC (aarch64).

ktuberling is the KDE "potato game" (MR. Potato Head style drawing game):
a Qt6/KF6 QWidget application built on the KDEGames6 library (libkdegames
26.04.0, published on the ohpcd registry). Upstream ships one executable:

  - ktuberling    the GUI game (QApplication main window; --version is
                  handled by KAboutData::setupCommandLine before the GUI
                  is created)

OHOS-specific adaptations:
  - patches/0001-ohos-skip-kdoctools-printsupport.patch: KF6 DocTools
    removed from the REQUIRED component list (kdoctools is not part of
    the published KF6 6.18/6.26 closure; doc/ subdirectory and
    kdoctools_install(po) are already guarded upstream by
    KF6DocTools_FOUND) and Qt6 PrintSupport removed from find/link (the
    ohpcd qtbase builds FEATURE_printsupport=OFF; conducteo 5.0.2 /
    algobox 1.1.1 precedent).
  - patches/0002-ohos-guard-printsupport.patch: QPrinter/QPrintDialog/
    filePrint/print action guarded with __has_include(<QPrintDialog>).
    The published qtbase qconfig does not define QT_NO_PRINTER, so the
    feature macro alone does not work; __has_include is a build-time
    compile check that makes the print path disappear when Qt
    PrintSupport is absent. Only direct printing is lost, the "Save as
    Picture" path (QtGui) is untouched.
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a gettext toolchain; catalogs are not needed for
    the smoke-verified deliverable).
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1 (Qt6
    Core/Gui/Widgets/Xml), qtmultimedia 6.11.1 (Qt6::
    Multimedia for the sound theme engine), qtsvg 6.11.1 (Qt6::Svg +
    Qt6::SvgWidgets), KF6 6.18.0 framework set, libkdegames 26.04.0
    (KDEGames6), ecm 6.26.0 (tool_requires).
  - KIO: the registry publishes kio/6.14.0 and kio/6.26.0 only. kio/6.14.0
    is used and its internal KF requires are lifted to the 6.18.0 closure
    with override=True (the same mechanism libkdegames uses for karchive):
    the KF6 minor releases are forward-compatible, kio 6.14 sources
    compile against 6.18 headers, and conan rebuilds kio from its
    published recipe against the 6.18 closure (--build=missing).
  - karchive/6.18.0 pinned with override=True (libkdegames 26.04.0 graph
    precedent: the newest kiconthemes/6.18.0 recipe revision requires
    karchive/6.19.0 which conflicts with knewstuff/6.18.0).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH.
  - Upstream registers no test suite (no tests/, autotests/ or add_test()
    anywhere in the tarball; N=0). Consumer-side verification is provided
    by test_package (ktuberling --version smoke, kfourinline 26.04.0
    pattern).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KtuberlingConan(ConanFile):
    name = "ktuberling"
    version = "26.04.0"
    description = (
        "KDE potato game (KTuberling) - Qt6/KF6 drawing game application "
        "built on KDEGames6/libkdegames"
    )
    license = "GPL-2.0-or-later AND GFDL-1.2-only"
    homepage = "https://invent.kde.org/games/ktuberling"
    url = "https://invent.kde.org/games/ktuberling"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        self.requires("qtsvg/6.11.1")
        # override=True also on the kio-overlapped requires: kio/6.14.0
        # pins these at exactly 6.14.0 internally, which would conflict
        # with libkdegames' exact 6.18.0 pins.
        self.requires("kconfig/6.18.0", override=True)
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0", override=True)
        self.requires("kcrash/6.18.0", override=True)
        self.requires("kdbusaddons/6.18.0")
        self.requires("ki18n/6.18.0", override=True)
        self.requires("kwidgetsaddons/6.18.0", override=True)
        self.requires("kxmlgui/6.18.0")
        self.requires("kiconthemes/6.18.0", override=True)
        self.requires("kcompletion/6.18.0", override=True)
        self.requires("kio/6.14.0")
        self.requires("libkdegames/26.04.0")
        # karchive: force the 6.18.0 line for the whole graph (libkdegames
        # 26.04.0 precedent: the newest kiconthemes/6.18.0 recipe revision
        # requires karchive/6.19.0, which conflicts with knewstuff/6.18.0
        # (karchive/6.18.0)). The override pins the compatible 6.18.0 so
        # the KF6 6.18 closure stays consistent.
        self.requires("karchive/6.18.0", override=True)
        # kio/6.14.0 internally requires KF frameworks at 6.14.0; lift the
        # whole graph onto the 6.18.0 closure (libkdegames/26.04.0 pins
        # kconfig/kcoreaddons/ki18n/... at exactly 6.18.0). KF6 minor
        # releases are forward-compatible; conan rebuilds kio from its
        # published recipe against the 6.18 closure (--build=missing).
        for dep in (
            "kservice", "kcolorscheme", "kguiaddons", "kitemviews",
            "kjobwidgets", "kwindowsystem", "kauth", "solid", "kbookmarks",
        ):
            self.requires(f"{dep}/6.18.0", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog processing needs the gettext msgfmt toolchain; skip it
        # (kfourinline 26.04.0 / audiocd 26.04.3 precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # OHOS loader workaround (audiocd 26.04.3 precedent): default lld
        # 0x10000 max-page-size can split .dynsym/.dynstr into separate
        # high-address RW LOAD segments which the OHOS musl loader refuses
        # to mmap; pin the 4K page layout.
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        # Qt6 split-package component discovery: Qt6Svg/SvgWidgets live in
        # the qtsvg package, Qt6Multimedia in qtmultimedia (libkdegames
        # verified pattern).
        qt_extra = []
        for dep_name in ("qtsvg", "qtmultimedia"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        # qtbase/KF6/libkdegames packages use cmake_find_mode=none, so
        # CMakeDeps doesn't put their lib/cmake dirs on CMAKE_PREFIX_PATH.
        # Write conan_cmakedeps_paths.cmake manually (libkdegames precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools (moc/uic/rcc/kconfig_compiler) shipped by the conan
        # packages are OHOS binaries: they need the compatible
        # libc++_shared from /system/lib64 plus the dependency lib dirs on
        # LD_LIBRARY_PATH (audiocd 26.04.3 / kconfig 6.26.0 precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory; CI workers may not export it via
            # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64 so
            # the loader resolves the compatible libc++ first (kconfig
            # 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: one executable in bin/, no library
        # deliverable (ktuberling links KDEGames6/KIOCore at runtime).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # Runtime env for consumers: the game needs KDEGames6/Qt6/KF6 libs
        # plus the QML import path of KDEGames6 (reflection scene plugin).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                self.runenv_info.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
