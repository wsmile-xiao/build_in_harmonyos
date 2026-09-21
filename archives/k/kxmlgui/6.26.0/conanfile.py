#!/usr/bin/env python3
"""Conan recipe for kxmlgui 6.26.0 on HarmonyOS PC.

kxmlgui is a KDE Frameworks 6 library providing XML-based user interface
framework (libKF6XmlGui.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - FORCE_DISABLE_KGLOBALACCEL=ON: KF6GlobalAccel is not published to ohpcd,
    global shortcut support is disabled
  - USE_DBUS=OFF (Qt6 DBus not published to ohpcd in the qtbase baseline)
  - BUILD_DESIGNERPLUGIN=OFF (Qt6UiPlugin not published to ohpcd)
  - BUILD_PYTHON_BINDINGS=OFF (Shiboken6/PySide6 not in the baseline)
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation
  - BUILD_TESTING=ON and ctest execution for upstream autotests available in
    the current headless feature set
  - Qt6PrintSupport removed (patch 0001/0002/0003): the qtbase baseline does
    not ship the PrintSupport module; the KShortcutsDialog Print action is
    dropped and the internal print slot is left inert
  - KF6ConfigWidgets dependency floor lowered 6.26.0 -> 6.18.0 (patch 0001):
    kconfigwidgets is only published at 6.18.0 on ohpcd; the rest of the KF6
    chain uses the 6.26.0 line
  - Dependencies: qtbase/6.11.1, kconfig/6.26.0, kconfigwidgets/6.18.0
    (transitive deps overridden to the 6.26.0 line), kcoreaddons/6.26.0,
    kguiaddons/6.26.0, ki18n/6.26.0, kiconthemes/6.26.0 (also provides
    libKF6IconWidgets.so + the KF6::IconWidgets imported target),
    openssl/3.5.6.1 (for KF6ArchiveConfig find_dependency(OpenSSL)),
    zstd/1.5.7 (for KF6ArchiveTargets PkgConfig::LibZstd),
    kitemviews/6.26.0, kwidgetsaddons/6.26.0, ecm/6.26.0
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KxmlguiConan(ConanFile):
    name = "kxmlgui"
    version = "6.26.0"
    description = "KDE Frameworks 6 - KDE XML GUI"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kxmlgui"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # KF6 6.26 line (published to ohpcd). kconfig/kcoreaddons/kguiaddons/
        # ki18n/kwidgetsaddons are declared once below with override=True:
        # in Conan 2 the override form both pins the whole graph to this
        # version and adds it as a direct requirement (a duplicated plain
        # requires for the same ref is rejected).
        self.requires("kiconthemes/6.26.0")
        self.requires("kitemviews/6.26.0")
        # kconfigwidgets cap: only 6.18.0 is published on ohpcd. Its own
        # recipe pins the 6.18 line for its transitive KF6 deps; those are
        # overridden here so the whole graph resolves to the 6.26 line
        # (otherwise conan rejects kconfig/6.18.0 vs kconfig/6.26.0 in the
        # same graph). The kconfigwidgets binary still links against the
        # 6.18-built shared libraries by SONAME; the KF6 libraries keep ABI
        # compatibility within the 6.x series, and the override guarantees
        # that exactly one 6.26 copy of each library is present at runtime.
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        # kcolorscheme/kcodecs are not direct kxmlgui deps; the override
        # entries redirect kconfigwidgets' 6.18 pins to the 6.26 line.
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        # kiconthemes -> karchive chain exports KF6ArchiveConfig.cmake which
        # activates find_dependency(OpenSSL) and PkgConfig::LibZstd
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")

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
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # KF6GlobalAccel / Qt6 DBus / Qt6UiPlugin are not published to ohpcd;
        # disable the corresponding features.
        tc.variables["FORCE_DISABLE_KGLOBALACCEL"] = "ON"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        # Python3/Shiboken6/PySide6 bindings are not built on OHOS.
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"
        # The initial KF 6.26 baseline does not ship translated catalogs.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

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
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(KF6*) and
            # transitive find_dependency() chains all resolve.
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
            openssl = self.dependencies.get("openssl")
            if openssl and openssl.package_folder:
                openssl_pkg = openssl.package_folder
                lines.append(f'set(OPENSSL_ROOT_DIR "{openssl_pkg}" CACHE PATH "")')
                lines.append(
                    f'set(OPENSSL_INCLUDE_DIR "{openssl_pkg}/include" '
                    f'CACHE PATH "")'
                )
                lines.append(
                    f'set(OPENSSL_CRYPTO_LIBRARY '
                    f'"{openssl_pkg}/lib/libcrypto.a" CACHE FILEPATH "")'
                )
                lines.append(
                    f'set(OPENSSL_SSL_LIBRARY '
                    f'"{openssl_pkg}/lib/libssl.a" CACHE FILEPATH "")'
                )
            zstd = self.dependencies.get("zstd")
            if zstd and zstd.package_folder:
                zstd_pkg = zstd.package_folder
                zstd_libs = [
                    os.path.join(zstd_pkg, "lib", "libzstd.so"),
                    os.path.join(zstd_pkg, "lib", "libzstd.a"),
                ]
                zstd_lib = next(
                    (path for path in zstd_libs if os.path.exists(path)),
                    zstd_libs[0],
                )
                lines.append("if(NOT TARGET PkgConfig::LibZstd)")
                lines.append("  add_library(PkgConfig::LibZstd UNKNOWN IMPORTED)")
                lines.append(
                    "  set_target_properties(PkgConfig::LibZstd PROPERTIES"
                )
                lines.append(f'    IMPORTED_LOCATION "{zstd_lib}"')
                lines.append(
                    f'    INTERFACE_INCLUDE_DIRECTORIES "{zstd_pkg}/include"'
                )
                lines.append("  )")
                lines.append("endif()")
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
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(self.build_folder, "bin"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        # Sandbox libc++_shared.so shadowing (kconfig 6.26.0 precedent).
        runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _run_upstream_tests(self):
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
        self._prepare_ctest_runtime_links()
        self._patch_ctest_qt_plugin_path()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _qt_plugin_path(self):
        plugin_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    plugin_dir = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(plugin_dir):
                        plugin_dirs.append(plugin_dir)
        plugin_dirs.append(os.path.join(self.build_folder, "bin"))
        return os.pathsep.join(plugin_dirs)

    def _patch_ctest_qt_plugin_path(self):
        build_bin = os.path.join(self.build_folder, "bin")
        full_plugin_path = self._qt_plugin_path()
        needle = f"QT_PLUGIN_PATH={build_bin}"
        replacement = f"QT_PLUGIN_PATH={full_plugin_path}"
        for test_file in glob.glob(
            os.path.join(self.build_folder, "**", "CTestTestfile.cmake"),
            recursive=True,
        ):
            with open(test_file) as f:
                content = f.read()
            if needle in content:
                with open(test_file, "w") as f:
                    f.write(content.replace(needle, replacement))

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

    def package_info(self):
        # The project installs its own KF6XmlGuiConfig.cmake with proper
        # dependency tracking (find_dependency on KF6Config etc). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6XmlGui"]
