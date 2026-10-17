#!/usr/bin/env python3
"""Conan test_package for kcalendarcore 6.26.0.

Verifies that the KF6CalendarCore library can be found via CMake and that
the MemoryCalendar/Event/Todo/ICalFormat APIs are callable (R34: real API
usage, including a libical-backed ICal parse round-trip).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KCalendarCoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("libical/4.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        libical = self.dependencies.get("libical")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        if libical:
            ical_pkg = libical.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{ical_pkg}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{ical_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{ical_pkg}/include")'
            )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; CI workers may not export it via LD_LIBRARY_PATH
        # (observed on OpenHarmonyPCDeveloper-CI-021). Prepend it so CMake's
        # TryCompile can link. Must not clobber conanbuild env on other hosts.
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        env = Environment()
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        # libical 4.0.1 ships OHOS relative sonames ("./libical.so"): the
        # musl loader resolves DT_NEEDED entries containing a slash from the
        # process CWD, not from LD_LIBRARY_PATH. ctest runs test_kcalendarcore
        # with CWD = the CMake build dir, so drop copies of the libical
        # libraries there (libical test_package precedent).
        libical = self.dependencies.get("libical")
        if libical and libical.package_folder:
            for lib_src in sorted(
                glob.glob(
                    os.path.join(libical.package_folder, "lib", "libical*.so")
                )
            ):
                lib_dst = os.path.join(
                    self.build_folder, os.path.basename(lib_src)
                )
                if not os.path.exists(lib_dst):
                    shutil.copy2(lib_src, lib_dst)
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kcalendarcore"),
                env="conanrun",
            )
