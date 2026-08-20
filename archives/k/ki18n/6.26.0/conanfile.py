#!/usr/bin/env python3
"""Conan recipe for ki18n 6.26.0 on HarmonyOS PC.

ki18n is a KDE Frameworks 6 internationalization library
(libKF6I18n.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_WITH_QML=OFF: the Qt6 Qml module is not published to ohpcd;
    scripted translations are disabled (the core library does not need it)
  - BUILD_TESTING=OFF to skip upstream tests during Conan build
  - Dependencies: qtbase/6.11.1 (Qt6Core/Qt6Widgets), ecm/6.26.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Ki18nConan(ConanFile):
    name = "ki18n"
    version = "6.26.0"
    description = "KDE Frameworks 6 - KDE Gettext-based UI text internationalization"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/ki18n"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # libintl is part of gettext; published gettext/0.22.5 provides
        # lib/libintl.a and include/libintl.h for ki18n's FindLibIntl.
        self.requires("gettext/0.22.5")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt6 Qml is not published to ohpcd; disable scripted translations.
        tc.variables["BUILD_WITH_QML"] = "OFF"

        # ki18n's FindLibIntl looks for libintl.h/libintl.a. Use the
        # published gettext package (libintl is part of gettext) to provide
        # them, so find_path/find_library succeed on any environment.
        gettext = self.dependencies.get("gettext")
        if gettext:
            tc.variables["CMAKE_INCLUDE_PATH"] = os.path.join(
                gettext.package_folder, "include")
            tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(
                gettext.package_folder, "lib")

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            # Also add gettext include/lib paths so FindLibIntl finds
            # libintl.h and libintl.a. The tc.variables CMAKE_INCLUDE_PATH
            # / CMAKE_LIBRARY_PATH set above become CACHE variables in
            # conan_toolchain.cmake; when conan_cmakedeps_paths.cmake
            # exists, the else()-block list(PREPEND) that would add
            # gettext paths is skipped, so we must add them here.
            if gettext:
                gettext_inc = os.path.join(gettext.package_folder, "include")
                gettext_lib = os.path.join(gettext.package_folder, "lib")
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{gettext_lib}")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{gettext_inc}")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
            # CI worker (buildbot) 缺 lld 依赖 libxml2.so.16 的 LD_LIBRARY_PATH：
            # lld 的 RUNPATH=$ORIGIN/../lib 在 musl ld 下可能不解析，导致
            # "Error loading shared library libxml2.so.16 / xmlFreeDoc: symbol not found"
            # （与 allegro5 同源）。动态探测 llvm lib 目录并注入 LD_LIBRARY_PATH。
            cc_cfg = self.conf.get("tools.build:compiler_executables", default={})
            cc = cc_cfg.get("c") if isinstance(cc_cfg, dict) else None
            if not cc:
                cc = os.environ.get("CC")
            if cc:
                cc_dir = os.path.dirname(
                    os.path.realpath(cc) if os.path.islink(cc) else cc
                )
                llvm_candidates = [
                    os.path.join(
                        cc_dir, "..", "ohos-sdk.org", "*",
                        "ohos", "native", "llvm", "lib",
                    ),
                    os.path.join(cc_dir, "..", "lib"),
                ]
                for pattern in llvm_candidates:
                    matches = glob.glob(pattern)
                    if matches:
                        llvm_lib = os.path.realpath(matches[0])
                        ld_path = os.environ.get("LD_LIBRARY_PATH", "")
                        os.environ["LD_LIBRARY_PATH"] = (
                            f"{llvm_lib}:{ld_path}" if ld_path else llvm_lib
                        )
                        self.output.info(f"ki18n: LD_LIBRARY_PATH += {llvm_lib}")
                        break
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6I18nConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6I18n"]
