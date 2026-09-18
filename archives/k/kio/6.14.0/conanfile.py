#!/usr/bin/env python3
"""Conan recipe for kio 6.14.0 on HarmonyOS PC.

kio is the KDE Frameworks 6 input/output and networking library
(libKF6KIOCore.so / libKF6KIOWidgets.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - USE_DBUS=OFF: the Qt6 DBus module and KF6DBusAddons are not published to
    ohpcd
  - WITH_X11=OFF / WITH_WAYLAND=OFF: no X11/Wayland session on OHOS
  - BUILD_DESIGNERPLUGIN=OFF (Qt6UiPlugin not published to ohpcd)
  - BUILD_TESTING=OFF to skip upstream tests during Conan build
  - Dependencies: qtbase/6.11.1, and KF6 packages already published to ohpcd
    (karchive, kconfig, kcoreaddons, ki18n, kservice, solid, kcrash,
    kbookmarks, kcolorscheme, kcompletion, kguiaddons, kiconthemes,
    kitemviews, kjobwidgets, kwidgetsaddons, kwindowsystem, kauth),
    ecm/6.20.0
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KioConan(ConanFile):
    name = "kio"
    version = "6.14.0"
    description = "KDE Frameworks 6 - KIO (input/output and networking)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kio"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("karchive/6.14.0")
        self.requires("kconfig/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kservice/6.14.0")
        self.requires("solid/6.14.0")
        self.requires("kcrash/6.14.0")
        self.requires("kbookmarks/6.14.0")
        self.requires("kcolorscheme/6.14.0")
        self.requires("kcompletion/6.14.0")
        self.requires("kguiaddons/6.14.0")
        self.requires("kiconthemes/6.14.0")
        self.requires("kitemviews/6.14.0")
        self.requires("kjobwidgets/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kwindowsystem/6.14.0")
        self.requires("kauth/6.14.0")
        # lld (OHOS SDK) needs libxml2.so.16 at link time; libxml2/2.15.3
        # provides that SONAME. Declared so its lib dir can be injected into
        # LD_LIBRARY_PATH below (Worker environments lack a system libxml2.so.16).
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # kio uses C++20 features (std::ranges); profile cppstd is 17.
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt6 DBus / X11 / Wayland components are not published to ohpcd;
        # disable the corresponding features.
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["WITH_X11"] = "OFF"
        tc.variables["WITH_WAYLAND"] = "OFF"
        # Qt Designer plugin requires Qt6UiPlugin, not published to ohpcd.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"

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

        # Worker lld needs libxml2.so.16 (SONAME of libxml2/2.15.3); inject
        # its lib dir into LD_LIBRARY_PATH so the linker can load it.
        libxml2 = self.dependencies.get("libxml2")
        if libxml2:
            libxml2_lib = os.path.join(libxml2.package_folder, "lib")
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", libxml2_lib)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", libxml2_lib)

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(KF6*)
            # and transitive find_dependency() chains all resolve.
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
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
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # NOTE: no post-install ELF rewriting here. In-place patchelf edits of
        # the packaged .so files are denied exec by the OHOS HMDFS W^X policy
        # (modified files get security.isolate labels and fail to load with
        # EACCES), so DT_NEEDED repair must happen at link time instead: patch
        # 0015 adds -Wl,-soname to the four KIO libraries, which makes the
        # linker record bare filenames for all intra-project DT_NEEDED
        # entries. Absolute DT_NEEDED entries pointing at conan-cache paths of
        # the external KF6 dependencies remain (resolvable on the build
        # device); this matches the rest of the KF6 family in this repo.

    def package_info(self):
        # The project installs its own KF6KIOConfig.cmake with proper
        # dependency tracking (find_dependency on KF6CoreAddons etc). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6KIOCore", "KF6KIOWidgets"]
        # kio installs headers under include/KF6/<Component>/ (with KIO/*.h
        # forwarding headers); expose each component dir so CMakeDeps-
        # generated targets carry correct include paths — otherwise
        # <KIO/KProtocolInfo> etc. cannot be resolved by consumers.
        self.cpp_info.includedirs = [
            os.path.join("include", "KF6", "KIOCore"),
            os.path.join("include", "KF6", "KIO"),
            os.path.join("include", "KF6", "KIOGui"),
            os.path.join("include", "KF6", "KIOWidgets"),
            os.path.join("include", "KF6", "KIOFileWidgets"),
        ]
