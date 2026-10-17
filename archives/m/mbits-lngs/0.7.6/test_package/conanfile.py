#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/mbits-lngs/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MbitslngsTestConan(ConanFile):
    test_type = "explicit"
    # Matches this repository's Conan 2 test_package recipe convention.
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # VirtualBuildEnv exports PkgConfigDeps' PKG_CONFIG_PATH for the optional lngs.pc consumer.
    # VirtualRunEnv supplies the conanrun environment used by self.run(..., env="conanrun").
    generators = "CMakeDeps", "PkgConfigDeps", "CMakeToolchain", "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def validate(self):
        # Keep this OHOS gate in sync with the tested recipe's validate() when adding targets.
        # The tested package is static-only, so reject shared=True explicitly here too.
        if self.options.shared:
            raise ConanInvalidConfiguration("mbits-lngs test_package only supports shared=False")
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("mbits-lngs test_package is currently validated for OHOS only")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _abs_build_dir(self, folder):
        if os.path.isabs(folder):
            return folder
        return os.path.join(self.build_folder, folder)

    def _shared_consumer_dir(self, bindir, libdir):
        for folder in (libdir, bindir):
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                if not name.startswith(("libtest_mbits_lngs_shared.", "test_mbits_lngs_shared.")):
                    continue
                if name.endswith((".so", ".dylib", ".dll")):
                    return folder
        raise ConanException("mbits-lngs shared consumer library was not produced")

    def test(self):
        # L0d rejects a test() that never calls self.run(). can_run skips execution
        # only for a real cross build; the OHOS host profile still runs the binaries.
        if not can_run(self):
            self.output.info("Cross-building: skip running mbits-lngs consumer binaries")
            return
        bindir = self._abs_build_dir(self.cpp.build.bindir)
        libdir = self._abs_build_dir(self.cpp.build.libdir)
        main_bin = os.path.join(bindir, "test_mbits_lngs")
        self.run(f'"{main_bin}"', env="conanrun")
        pkgconfig_bin = os.path.join(bindir, "test_mbits_lngs_pkgconfig")
        if os.path.isfile(pkgconfig_bin):
            self.run(f'"{pkgconfig_bin}"', env="conanrun")
        runner = os.path.join(bindir, "test_mbits_lngs_shared_runner")
        shared_dir = self._shared_consumer_dir(bindir, libdir)
        self.run(f'"{runner}"', env="conanrun", cwd=shared_dir)
        cmake = CMake(self)
        cmake.test()
