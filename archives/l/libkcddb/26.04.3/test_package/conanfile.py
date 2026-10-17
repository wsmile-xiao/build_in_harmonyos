#!/usr/bin/env python3
"""Conan test_package for libkcddb 26.04.3.

Verifies that the KCddb6 library can be found via CMake and that the
offline-capable core API (CDInfo field round trip, xmcd serialization,
Categories/Genres helpers) is callable (R34: real API usage).

Network lookups (KCDDB::Client) are intentionally NOT exercised here: the
CI sandbox has no internet access (network-dependent test exemption).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibkcddbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The tested package, qtbase and kconfig all use cmake_find_mode=none,
        # so the generated conan_cmakedeps_paths.cmake would not contain their
        # lib/cmake dirs. Create it manually (recipe precedent:
        # kdegraphics-mobipocket 26.04.1).
        qtbase = self.dependencies.get("qtbase")
        kconfig = self.dependencies.get("kconfig")
        libkcddb = self.dependencies.get("libkcddb")
        lines = []
        for dep in (qtbase, kconfig, libkcddb):
            if dep:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
        if qtbase:
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qtbase.package_folder}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qtbase.package_folder}/include")'
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
        # "../../bin/libKF6ConfigCore.so" (a build-tree rpath baked in at
        # kconfig packaging time). The dynamic linker resolves it relative
        # to the location of the binary that first pulls it in, so provide
        # the file at <executable_dir>/../../bin AND <build_folder>/../bin
        # to satisfy it regardless of which binary triggers the load
        # (kconfig 6.26.0 recipe precedent, same workaround).
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
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, "bin")
            )
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
            with test_env.vars(self).apply():
                self.run(
                    os.path.join(self.cpp.build.bindirs[0], "test_package"),
                    cwd=self.build_folder,
                )
