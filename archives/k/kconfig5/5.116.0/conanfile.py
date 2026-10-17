#!/usr/bin/env python3
"""Conan recipe for KConfig KF5 5.116.0 on HarmonyOS PC.

KConfig is the KDE configuration system, providing the KConfig XT system for
configuration management.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KCONFIG_USE_DBUS=OFF / KCONFIG_USE_QML=OFF to drop Qt5DBus / Qt5Qml
    dependencies (not part of the published qt5-qtbase package)
  - ecm_install_po_files_as_qm(poqm) disabled via patch (requires
    Qt5LinguistTools, not present in the qt5-qtbase package)
  - BUILD_TESTING=ON and ctest execution for upstream autotests
  - Dependencies: qt5-qtbase/5.15.2.2 (includes Qt5Xml) and ecm/6.20.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)


class Kconfig5Conan(ConanFile):
    name = "kconfig5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - configuration system (KConfig XT)"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/kconfig"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        shared = bool(self.options.shared)
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt5DBus IS provided by the published qt5-qtbase package
        # (include/QtDBus + lib/cmake/Qt5DBus + libQt5DBus.so), so KConfig's
        # D-Bus component is kept ON to match the upstream default and let the
        # D-Bus related tests run.
        # Qt5Qml is NOT available (qt5-qtbase does not ship Qt5Qml), so the
        # optional KConfigQml component stays OFF. KConfigQml is a small
        # QML-integration helper (KDeclarative support) that is not needed by
        # the configuration core; enabling it would require pulling a
        # version-mismatched qt5-qtdeclarative/5.15.2 (qtbase is .5.15.2.2).
        tc.variables["KCONFIG_USE_DBUS"] = "ON"
        tc.variables["KCONFIG_USE_QML"] = "OFF"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"

        if str(self.settings.os) in ("Linux", "OHOS"):
            if str(self.settings.os) == "OHOS":
                # The OHOS CMake platform module does not define the SONAME
                # flag, so shared libraries ship without a DT_SONAME and
                # consumers record path-form DT_NEEDED like
                # "bin/libKF5ConfigCore.so" that the loader cannot resolve at
                # runtime (E537). The KF5 libs set VERSION/SOVERSION upstream,
                # so with the SONAME flag enabled lld emits a real soname and
                # the executable records the bare name.
                tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
                tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            targets = {
                "armv8": "aarch64-linux-ohos",
                "x86_64": "x86_64-linux-ohos",
            }
            target = targets.get(str(self.settings.arch))
            if target:
                tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = self._cmake_path(
                os.path.join(ecm.package_folder, "share", "ECM")
            )
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    f"{ecm_share}/modules",
                    f"{ecm_share}/find-modules",
                    f"{ecm_share}/kde-modules",
                ]
            )

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
            qt_pkg = self._cmake_path(qtbase.package_folder)
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_pkg = self._cmake_path(ecm.package_folder)
                ecm_cmake = f"{ecm_pkg}/share/ECM/cmake"
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _cmake_path(path):
        return os.fspath(path).replace("\\", "/")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # The qt5-qtbase conan package stores its full mkspec tree under
        # <pkg>/mkspecs.  Downstream Qt builds (KDE Frameworks CMake) compile
        # against the *build-side* mkspec path <pkg>/../b/mkspecs/linux-clang,
        # and that linux-clang/qplatformdefs.h does `#include
        # "../common/posix/qplatformdefs.h"`.  On a clean CI worker the
        # b/mkspecs dir is either missing or a symlink without the common/
        # subtree, so the relative include fails.  Mirror the whole mkspecs
        # tree from the package folder into b/mkspecs so common/posix is
        # always present.
        src_mkspecs = os.path.join(qt_package_folder, "mkspecs")
        dst_mkspecs = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs"
        )
        if os.path.isdir(src_mkspecs):
            for rel in ("linux-clang", "common"):
                src = os.path.join(src_mkspecs, rel)
                dst = os.path.join(dst_mkspecs, rel)
                if os.path.isdir(src) and not os.path.islink(dst) and not os.path.isdir(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copytree(src, dst)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        # The built KF5 libs have no DT_SONAME, so downstream executables
        # record a relative DT_NEEDED like "bin/libKF5ConfigCore.so". That
        # relative path only resolves when the build root (which contains the
        # "bin/" compat symlinks created by _prepare_ctest_runtime_links) is on
        # the library path.
        runtime_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, os.pardir)
        )
        return runtime_env

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.info(
                "Skipping upstream CTest during cross-compilation; target execution is required on OHOS"
            )
            return
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        test_env.define(
            "GIO_EXTRA_MODULES",
            os.path.join(self.build_folder, "giomodules"),
        )
        self._prepare_ctest_runtime_links()
        # Test exclusions: these upstream tests are not reproducible on OHOS
        # because of OS-level differences (verified with full HOME/XDG env):
        # - filesystem permission semantics in the sandbox (chmod readonly
        #   does not take effect, E046) -> sync() succeeds where upstream expects failure
        # - QFileSystemWatcher / KConfigWatcher notify events do not fire on
        #   the OHOS sandbox (no inotify), so QSignalSpy stays at 0
        excluded = "|".join(
            [
                "kconfigcore-kconfigtest",
                "kconfigcore-kdesktopfiletest",
                "kconfiggui-kstandardshortcutwatchertest",
            ]
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "({})"'.format(
                    self.build_folder, excluded
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._make_pkgconfig_relocatable()

    def _make_pkgconfig_relocatable(self):
        package_root = self._cmake_path(self.package_folder).rstrip("/")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        for pc_file in glob.glob(os.path.join(pc_dir, "*.pc")):
            content = load(self, pc_file)
            content = content.replace(
                f"prefix={package_root}", "prefix=${pcfiledir}/../..", 1
            )
            content = content.replace(
                f"libdir={package_root}/lib", "libdir=${prefix}/lib", 1
            )
            content = content.replace(
                f"includedir={package_root}/include", "includedir=${prefix}/include", 1
            )
            content = content.replace(f"-L{package_root}/lib", "-L${libdir}")
            content = content.replace(f"-I{package_root}/include", "-I${includedir}")
            save(self, pc_file, content)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5ConfigCore", "KF5ConfigGui"]
        # KConfig5 同时构建命令行工具 kreadconfig5/kwriteconfig5 到 bin/（R38）
        self.cpp_info.bindirs = ["bin"]
