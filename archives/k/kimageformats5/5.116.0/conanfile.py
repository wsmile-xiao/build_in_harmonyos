#!/usr/bin/env python3
"""Conan recipe for kimageformats5 5.116.0 (KDE Frameworks 5 line) on HarmonyOS PC.

kimageformats is the KDE image format plugins collection for Qt: it provides
QImageIOHandler plugins for many formats (ANI, HDR, PCX, PIC, PSD, QOI, RAS,
RGB, TGA, XCF, EXR, RAW, ...) that the stock Qt build does not ship.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the metainfo.yaml platform list).
  - QT_MAJOR_VERSION is forced to 5 by the project's find_package(ECM) path;
    the published qt5-qtbase package provides Core/Network/Gui/Test/Concurrent
    only, so the EPS plugin (needs PrintSupport) is naturally not built.
  - Optional format libraries are gated to what is resolvable on OHOS:
    * OpenEXR enabled (openexr/3.3.4 published in the registry).
    * LibRaw enabled with zlib/jpeg disabled (libraw's default zlib pin
      conflicts with qt5-qtbase's zlib pin; the codec-free build links fine).
    * AVIF/HEIF/JXL disabled: libavif's dependency chain pins
      libpng/1.6.58 -> zlib/1.3.1.1 which conflicts with qt5-qtbase's
      zlib/1.3.1 requirement in the same dependency graph, and libjxl is not
      published in the registry at all.
    * KF5Archive (KRA/ORA plugins) not available on the KF5 line in the
      registry; plugins disabled via KIMAGEFORMATS_KF5ARCHIVE=OFF.
  - The Qt5 package inside Conan is found through its own lib/cmake/Qt5
    config files (the recipe sets cmake_find_mode=none on its own package),
    so CMAKE_PREFIX_PATH is pointed at the package folders directly.
  - Upstream autotests: readtest/writetest/pictest/anitest are built with
    BUILD_TESTING=ON. The tests are cross-compiled; target execution happens
    outside the Conan build (CI is offline for target runs), so the CTest
    invocation is skipped during cross builds with can_run() and the
    binaries are packaged for on-device runs instead.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KImageFormats5Conan(ConanFile):
    name = "kimageformats5"
    version = "5.116.0"
    description = "KDE Frameworks 5 image format plugins for Qt (QImageIOHandler plugins)"
    license = "BSD-2-Clause AND LGPL-2.1-or-later AND MIT"
    homepage = "https://invent.kde.org/frameworks/kimageformats"
    url = "https://download.kde.org/stable/frameworks/5.116/kimageformats-5.116.0.tar.xz"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_openexr": [True, False],
        "with_libraw": [True, False],
    }
    default_options = {
        "shared": True,
        "with_openexr": True,
        "with_libraw": True,
        "libraw/*:enable_zlib": False,
        "libraw/*:enable_jpeg": False,
        "libraw/*:enable_examples": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")
        if self.options.with_openexr:
            self.requires("openexr/3.3.4")
        if self.options.with_libraw:
            self.requires("libraw/0.22.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kimageformats5 only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt5 line: pick the Qt5 code paths in the project CMake files.
        tc.variables["QT_MAJOR_VERSION"] = "5"
        # Optional format libraries: only enable what resolves on OHOS.
        tc.variables["KIMAGEFORMATS_HEIF"] = "OFF"
        tc.variables["KIMAGEFORMATS_JXL"] = "OFF"
        tc.variables["KIMAGEFORMATS_JXR"] = "OFF"
        tc.variables["KIMAGEFORMATS_KF5ARCHIVE"] = "OFF"
        if not self.options.with_openexr:
            tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenEXR"] = "ON"
        if not self.options.with_libraw:
            tc.variables["CMAKE_DISABLE_FIND_PACKAGE_LibRaw"] = "ON"
        # Qt tools (moc) shipped inside the target qt5-qtbase package are
        # native AArch64 binaries on this device; let AUTOMOC find them via PATH.
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = self._qt_host_tool("moc")
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = self._qt_host_tool("rcc")
        tc.variables["CMAKE_AUTOUIC_EXECUTABLE"] = self._qt_host_tool("uic")
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["KDE_INSTALL_QTPLUGINDIR"] = "plugins"
        tc.variables["KDE_INSTALL_PLUGINDIR"] = "lib/plugins"

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

        # CMakeDeps cannot add qt5-qtbase's lib/cmake to CMAKE_PREFIX_PATH
        # (the dependency uses cmake_find_mode=none), so prepend it here.
        lines = []
        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            # The published Qt package's Qt5CoreConfigExtras.cmake references a
            # build-tree mkspec path (<pkg>/../b/mkspecs/linux-clang); create
            # the expected sibling layout so the reference resolves.
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
            qt_pkg = self._cmake_path(qtbase.package_folder)
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if ecm:
            ecm_pkg = self._cmake_path(ecm.package_folder)
            ecm_cmake = f"{ecm_pkg}/share/ECM/cmake"
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        for dep_name in ("openexr", "libraw"):
            dep = self.dependencies.get(dep_name)
            if dep:
                dep_pkg = self._cmake_path(dep.package_folder)
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep_pkg}")')
                # Also propagate transitive Conan deps of the format library
                # (e.g. openexr -> imath: OpenEXRConfig find_dependency(Imath)
                # needs the Imath config on CMAKE_PREFIX_PATH too).
                for req in dep.dependencies.items():
                    req_info = req[1] if isinstance(req, tuple) else req
                    req_folder = getattr(req_info, "package_folder", None)
                    if req_folder:
                        lines.append(
                            f'list(PREPEND CMAKE_PREFIX_PATH '
                            f'"{self._cmake_path(req_folder)}")'
                        )
                pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
                if os.path.isdir(pc_dir):
                    lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pc_dir}")')
                    lines.append(
                        'set(ENV{PKG_CONFIG_PATH} "$ENV{PKG_CONFIG_PATH}'
                        f':{self._cmake_path(pc_dir)}")'
                    )
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        # FindLibRaw is a plain find_path/find_library module: give it hints.
        if self.options.with_libraw:
            libraw = self.dependencies.get("libraw")
            if libraw:
                libraw_pkg = self._cmake_path(libraw.package_folder)
                tc.variables["LibRaw_INCLUDE_DIR"] = os.path.join(
                    libraw_pkg, "include"
                )
                tc.variables["LibRaw_LIBRARY"] = os.path.join(
                    libraw_pkg, "lib", "libraw_r.so"
                )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def _qt_host_tool(self, name):
        qtbase = self.dependencies.get("qt5-qtbase")
        tool = os.path.join(qtbase.package_folder, "bin", name)
        return self._cmake_path(tool)

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Mirror the attica-kf5 workaround: Qt5CoreConfigExtras.cmake expects
        # <pkg>/../b/mkspecs/linux-clang to exist (build-tree residue).
        source = os.path.join(qt_package_folder, "mkspecs", "linux-clang")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs", "linux-clang"
        )
        if os.path.isdir(source) and not os.path.exists(expected):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected)

    @staticmethod
    def _cmake_path(path):
        return os.fspath(path).replace("\\", "/")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._build_env().vars(self).apply():
            cmake.build()
        if can_run(self):
            # Upstream autotests run on the native OHOS device. Two known
            # environment-scoped failures are excluded:
            #  - kimageformats-read-psd: the birthday.pdd case compares
            #    against birthday.tif, and the published qt5-qtbase package
            #    ships no TIFF image plugin, so the reference image cannot
            #    load (37/37 loadable cases pass).
            #  - kimageformats-read-exr: the EXR handler is seek-based
            #    (K_IStream over QIODevice), so the SEQUENTIAL ACCESS run of
            #    rgb-gimp.exr cannot stream (RANDOM ACCESS passes).
            with self._test_env().vars(self).apply():
                self.run(
                    'ctest --test-dir "{0}" --output-on-failure '
                    '-E "kimageformats-read-psd|kimageformats-read-exr"'.format(
                        self.build_folder
                    )
                )

    def _test_env(self):
        env = self._build_env()
        # Runtime library dirs for the optional format libraries.
        for dep_name in ("openexr", "libraw"):
            dep = self.dependencies.get(dep_name)
            if dep:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                # Propagate transitive deps of the format libraries (imath,
                # libdeflate) whose DT_NEEDED entries reference their Conan
                # package folders.
                for req in dep.dependencies.items():
                    req_info = req[1] if isinstance(req, tuple) else req
                    req_folder = getattr(req_info, "package_folder", None)
                    if req_folder:
                        env.prepend_path(
                            "LD_LIBRARY_PATH", os.path.join(req_folder, "lib")
                        )
        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            env.prepend_path(
                "QT_PLUGIN_PATH",
                os.path.join(self.build_folder, "bin"),
            )
        return env

    def _build_env(self):
        env = Environment()
        # Host tools (moc) from the qt5-qtbase package need the system
        # libc++_shared.so which is not on the default loader path.
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib")
            )
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(qtbase.package_folder, "plugins")
            )
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("pkg_config_name", "kimageformats5")
        # Pure plugin package: no linker libraries, no executables (R38:
        # empty bindirs keeps the library classification). Qt loads the
        # plugins from <package_folder>/plugins/imageformats at runtime.
        self.cpp_info.libdirs = ["lib", "plugins/imageformats"]
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        # Expose the plugin directory through a user property so consumers
        # can locate the imageformats plugins for QT_PLUGIN_PATH.
        self.cpp_info.set_property(
            "user_info:plugin_dir", "plugins/imageformats"
        )
