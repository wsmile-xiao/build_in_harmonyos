#!/usr/bin/env python3
"""Conan recipe for kglobalaccel 6.26.0 on HarmonyOS PC.

kglobalaccel is a KDE Frameworks 6 tier-1 library (libKF6GlobalAccel.so)
providing global workspace shortcuts.

OHOS-specific adaptations (recipe layer, no source patches):
  - KF_IGNORE_PLATFORM_CHECK=TRUE: metainfo.yaml lists Linux/FreeBSD only and
    ECM's KDEMetaInfoPlatformCheck makes configure fail on HarmonyOS without
    this escape hatch.
  - WITH_X11=OFF: upstream defaults WITH_X11 to ON and src/kglobalaccel.cpp:26
    then includes <private/qtx11extras_p.h>; the OHOS qtbase / qtbase-sql-dbus
    builds have FEATURE_xcb/xlib=OFF and do not ship that private header.
  - Qt6::DBus is only provided by qtbase-sql-dbus/6.11.1 (qtbase/6.11.1 is
    built with FEATURE_dbus=OFF and ships no Qt6DBus cmake module).
  - qt6linguisttools/6.11.1 supplies Qt6::LinguistTools (lrelease), which
    ecm_install_po_files_as_qm(poqm) looks up with CONFIG REQUIRED; because
    the Qt modules live in separate package folders, the extra prefixes are
    announced through QT_ADDITIONAL_PACKAGES_PREFIX_PATH.
  - qtdeclarative/6.11.1 supplies Qt6::Qml, required by the upstream
    tests/CMakeLists.txt executable target.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KglobalaccelConan(ConanFile):
    name = "kglobalaccel"
    version = "6.26.0"
    description = "KDE Frameworks 6 - KGlobalAccel (global workspace shortcuts)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kglobalaccel"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Core/Gui/Widgets/DBus are all provided by qtbase-sql-dbus
        # (superset build of qtbase with FEATURE_dbus=ON).
        self.requires("qtbase-sql-dbus/6.11.1")
        # poqm translation compilation needs Qt6::LinguistTools (lrelease);
        # ecm_install_po_files_as_qm() looks it up with CONFIG REQUIRED.
        self.requires("qt6linguisttools/6.11.1")
        # tests/ links Qt6::Qml (upstream tests/CMakeLists.txt).
        self.requires("qtdeclarative/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        # metainfo.yaml declares platforms Linux/FreeBSD only; ECM's
        # KDEMetaInfoPlatformCheck aborts configure on HarmonyOS unless this
        # escape hatch is set (kcrash 6.26.0 precedent).
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Upstream defaults WITH_X11 to ON; HarmonyOS has no X11 and the Qt
        # private header private/qtx11extras_p.h is not shipped by the OHOS
        # qtbase/qtbase-sql-dbus builds (FEATURE_xcb/xlib=OFF), so
        # src/kglobalaccel.cpp:26 fails to compile unless X11 support is off.
        tc.variables["WITH_X11"] = "OFF"
        # CMake selects Platform/OHOS.cmake (which inherits the Linux SONAME
        # rule) only when CMAKE_SYSTEM_NAME=OHOS; Conan maps settings.os=OHOS
        # to CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake has no platform
        # module. The generic fallback leaves the SONAME flag undefined, so
        # CMake drops VERSION/SOVERSION and emits an unversioned .so without
        # DT_SONAME (L5 soname gate fails, downstream cannot link by SONAME).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qt_pkgs = [d for d in self.dependencies.values()
                   if d.package_folder and os.path.isdir(os.path.join(d.package_folder, "lib", "cmake"))]
        if qt_pkgs:
            # Qt split-module packages (qt6linguisttools, qtdeclarative, ...)
            # live in separate package folders than the Qt6 base config.
            # find_package(Qt6 COMPONENTS LinguistTools) resolves modules
            # relative to Qt6_DIR, so the extra prefixes must be announced
            # through Qt's own mechanism (QT_ADDITIONAL_PACKAGES_PREFIX_PATH).
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                d.package_folder for d in qt_pkgs
            )
            linguist = self.dependencies.get("qt6linguisttools")
            if linguist:
                tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
                    linguist.package_folder, "lib", "cmake", "Qt6LinguistTools"
                )
            lines = []
            # qtbase/qtbase-sql-dbus use cmake_find_mode=none, so CMakeDeps does
            # not emit conan_cmakedeps_paths.cmake; create it manually.
            for dep in qt_pkgs:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
            # qtbase-sql-dbus must win the find_package(Qt6) lookup: it is the
            # only provider of Qt6::DBus (qtbase ships FEATURE_dbus=OFF), and it
            # also ships the full Core/Gui/Widgets/Test set.
            sqldbus = self.dependencies.get("qtbase-sql-dbus")
            if sqldbus:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{sqldbus.package_folder}/lib/cmake")')
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                runtime_env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so other
        # platforms are unaffected (kcrash 6.26.0 precedent).
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6GlobalAccel"]
