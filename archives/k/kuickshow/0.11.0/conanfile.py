#!/usr/bin/env python3
"""Conan recipe for kuickshow 0.11.0 on HarmonyOS PC.

kuickshow is the KDE quick image viewer (Qt6 Widgets + KF6): a fast
browser/viewer with an optional Imlib1/Imlib2 image backend. With both
USE_IMLIB1 and USE_IMLIB2 off (the default, and the only mode usable on
OHOS - Imlib would pull in X11), the viewer falls back to the pure-Qt
backend (src/imlib_qt.cpp) and needs neither X11 nor Imlib.

Upstream registers no test suite (no tests/, autotests/ or add_test() in
the tarball - grep verified). Consumer-side verification is provided by
test_package: the installed kuickshow binary is executed with --version
under QT_QPA_PLATFORM=offscreen (R34) and the packaged data files
(misc/im_palette.pal palette contract + pics/ app data) plus the desktop
entry and icons are verified.

OHOS adaptations (patches/0001 + patches/0002):

* Qt6 PrintSupport trimmed (patch 0001): the published qtbase/6.11.1
  package ships only Core/Gui/Widgets/Network/Sql/Test/DBus/Concurrent/Xml
  - no libQt6PrintSupport.so and no Qt6PrintSupport cmake config. Upstream
  printing (src/printing.cpp + printing_page.ui, QPrinter/QPrintDialog)
  is removed from the build; the "Print Image" actions stay registered
  but report platform unavailability via KMessageBox::information.
* KF6 DocTools trimmed (patch 0001): the kdoctools handbook toolchain is
  not part of the platform package set (kfourinline 26.04.0 / kgoldrunner
  26.04.0 precedent); doc/ and the KF6DocTools component are dropped.
* C++17 (patch 0002): upstream pins CMAKE_CXX_STANDARD 11, the KF6 6.14
  headers require C++17 (kio 6.14.0 recipe sets 20 for the same reason).

Dependency line: qtbase/6.11.1 + the published KF6 6.14.0 baseline line
(same closure as kio/6.14.0 and kxmlgui/6.14.0 - kconfig, kconfigwidgets,
kcoreaddons, kcrash, ki18n, kiconthemes, kitemviews, kjobwidgets,
ktextwidgets, kwidgetsaddons, kwindowsystem, kcompletion, kcodecs,
kbookmarks, kguiaddons, kcolorscheme, kauth, solid, kservice, karchive),
ecm/6.20.0 as the build tool (kio 6.14.0 / keditbookmarks 26.04.0
precedent).

Runtime environment: kuickshow is a QApplication; on the OHOS worker it
runs with QT_QPA_PLATFORM=offscreen (kgoldrunner 26.04.0 / audiocd
26.04.3 test precedent). The consumer test only executes --version, no
window is shown.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class KuickshowConan(ConanFile):
    name = "kuickshow"
    version = "0.11.0"
    description = ("KDE KuickShow - a fast and versatile image viewer "
                   "(Qt6 Widgets + KF6, pure-Qt image backend)")
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/graphics/kuickshow"
    url = "https://invent.kde.org/graphics/kuickshow/-/archive/v0.11.0/kuickshow-v0.11.0.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published KF6 6.14.0 baseline line (same closure as kio/6.14.0
        # and kxmlgui/6.14.0) so the whole graph reuses published binaries
        # built against the same qtbase/6.11.1 (no Qt6DBus / Qt6PrintSupport).
        self.requires("qtbase/6.11.1")
        self.requires("ki18n/6.14.0")
        self.requires("kiconthemes/6.14.0")
        self.requires("kio/6.14.0")
        self.requires("kwindowsystem/6.14.0")
        self.requires("kxmlgui/6.14.0")
        # kio/6.14.0 link-time requirement: the OHOS SDK lld depends on
        # libxml2.so.16 (libxml2/2.15.3 SONAME); its lib dir is injected
        # into LD_LIBRARY_PATH (kio / keditbookmarks recipe precedent).
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kuickshow is adapted for Linux and OHOS, not "
                f"{self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip translation catalog generation (kgoldrunner 26.04.0 /
        # audiocd 26.04.3 precedent: the CI worker msgfmt fails to load
        # its own libintl).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # The KF6DocTools component is trimmed by patch 0001; never let
        # find_package look for it (it would fail hard on the OHOS set).
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"
        # Pure-Qt image backend: no Imlib, no X11 (both default OFF; set
        # explicitly so a stray cache entry cannot turn them on).
        tc.variables["USE_IMLIB1"] = "OFF"
        tc.variables["USE_IMLIB2"] = "OFF"
        # KDEInstallDirs single-prefix layout on conan (libkdegames /
        # kgoldrunner precedent).
        tc.variables["KDE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated one does not (audiocd precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )
        if self.settings.os == "OHOS":
            # OHOS loader workaround (audiocd precedent): pin page size.
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
        tc.generate()

        # qtbase and the KF6 packages use cmake_find_mode=none, so
        # CMakeDeps does not generate conan_cmakedeps_paths.cmake. Create it
        # manually (audiocd / kgoldrunner precedent).
        lines = []
        # include every package whose cmake config may be reached through
        # find_dependency chains (KF6 configs find_dependency each other);
        # host dependencies + build tools (ecm) both contribute prefixes.
        all_pkgs = {}
        for dep in self.dependencies.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep in self.dependencies.host.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep in self.dependencies.build.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep_name in sorted(all_pkgs):
            pkg = all_pkgs[dep_name]
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            for libdir in ("lib", "lib64"):
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/{libdir}")'
                )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")'
            )
            bindir = os.path.join(pkg, "bin")
            if os.path.isdir(bindir):
                lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{bindir}")')
        if ecm:
            ecm_pkg = ecm.package_folder
            ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm_pkg}/bin")')
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools (moc / uic / rcc, kconfig_compiler) may be OHOS
        # binaries needing libc++_shared from /system/lib64 plus the
        # dependency lib dirs on LD_LIBRARY_PATH (audiocd 26.04.3 /
        # kgoldrunner precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        copy(self, "LICENSES",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.build_modules["cmake_find_package"].append(
            os.path.join("lib", "cmake")
        )
        # Runtime helpers for consumers (test_package) - app data is
        # installed under share/kuickshow (palette + pics).
        self.runenv_info.prepend_path(
            "XDG_DATA_DIRS", os.path.join(self.package_folder, "share")
        )
