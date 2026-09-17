#!/usr/bin/env python3
"""Conan test_package for audiocd 26.04.3.

Verifies that the audiocdplugins library is consumable: the encoder base
interfaces (AudioCDEncoder / AudioCDDataSink), the wav/cda encoders
(RIFF header emission, raw frame pass-through, size computations), the
KCDDB CDInfo type plumbing against the published libkcddb, and the
create_audiocd_encoders plugin symbol resolution (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class AudiocdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")
        # audiocdplugins public headers include <kcddb/CDInfo>
        self.requires("libkcddb/26.04.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The tested package, qtbase and the KF6 packages all use
        # cmake_find_mode=none, so the generated conan_cmakedeps_paths.cmake
        # would not contain their lib/cmake dirs. Create it manually
        # (libkcddb 26.04.3 recipe precedent).
        lines = []
        for dep_name in ("qtbase", "kconfig", "kcoreaddons", "ki18n", "audiocd", "libkcddb"):
            dep = self.dependencies.get(dep_name)
            if dep:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
        kcddb = self.dependencies.get("libkcddb")
        if kcddb and kcddb.package_folder:
            # The audiocdplugins public header includes <kcddb/CDInfo>; the
            # libkcddb package headers/libs are needed for the consumer
            # compile/link (it uses cmake_find_mode=none).
            lines.append(
                "set(CONAN_LIBKCDDB_INCLUDE "
                f'"{kcddb.package_folder}/include/KCddb6")'
            )
            lines.append(
                "set(CONAN_LIBKCDDB_LIB "
                f'"{kcddb.package_folder}/lib")'
            )
        audiocd_dep = self.dependencies.get("audiocd")
        if audiocd_dep and audiocd_dep.package_folder:
            lines.append(
                "set(CONAN_AUDIOCD_LIB "
                f'"{audiocd_dep.package_folder}/lib")'
            )
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qtbase.package_folder}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qtbase.package_folder}/include")'
            )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
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
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            # Qt host tools (moc) are OHOS binaries needing libc++_shared;
            # /system/lib64 provides the compatible one (kconfig recipe
            # precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with build_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _prepare_runtime_links(self):
        # kconfig's libKF6ConfigGui.so carries a relative DT_NEEDED entry
        # '../../bin/libKF6ConfigCore.so' (a build-tree rpath baked in at
        # kconfig packaging time). The dynamic linker resolves path-style
        # NEEDED entries relative to the process cwd, so provide the file at
        # <build_folder>/../../bin (libkcddb 26.04.3 recipe precedent).
        import shutil
        kconfig = self.dependencies.get("kconfig")
        if not kconfig:
            return
        compatibility_bins = set()
        exe_dir = os.path.dirname(
            os.path.join(self.build_folder, self.cpp.build.bindirs[0])
        )
        compatibility_bins.add(
            os.path.normpath(os.path.join(exe_dir, os.pardir, os.pardir, "bin"))
        )
        compatibility_bins.add(
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin"))
        )
        for compatibility_bin in compatibility_bins:
            os.makedirs(compatibility_bin, exist_ok=True)
            for lib_name in ("libKF6ConfigCore.so", "libKF6ConfigGui.so"):
                src = os.path.join(kconfig.package_folder, "lib", lib_name)
                dst = os.path.join(compatibility_bin, lib_name)
                if os.path.exists(src) and not os.path.exists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def test(self):
        if can_run(self):
            self._prepare_runtime_links()
            test_env = Environment()
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    test_env.prepend_path(
                        "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                    )
            if str(self.settings.os) == "OHOS":
                test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_home = os.path.join(self.build_folder, "test-home")
            os.makedirs(test_home, exist_ok=True)
            test_env.define("HOME", test_home)
            # Point the plugin-resolution checks at the installed plugin
            # directory (lib/plugins/ in the package layout).
            audiocd = self.dependencies.get("audiocd")
            if audiocd and audiocd.package_folder:
                # KDEInstallDirs single-prefix layout: the encoder plugins
                # install next to libaudiocdplugins.so in lib/.
                plugin_dir = os.path.join(audiocd.package_folder, "lib")
                if os.path.isdir(plugin_dir):
                    test_env.define("AUDIOCD_PLUGIN_DIR", plugin_dir)
            with test_env.vars(self).apply():
                self.run(
                    os.path.join(self.cpp.build.bindirs[0], "test_package"),
                    cwd=self.build_folder,
                )
