#!/usr/bin/env python3
"""Test package for dirent 1.26 — consumer verification via CMake target.

On HarmonyOS the platform libc already provides the POSIX dirent API; this
consumer links the package's CMake target `dirent` and exercises the public
dirent API (opendir/readdir/closedir/scandir/alphasort/telldir/seekdir)
against a real directory, verifying observable results.

To make the test genuinely depend on the package's installed artifacts, the
consumer loads the *shipped* DirentConfig.cmake directly from the package
folder (no CMakeDeps re-generation in the build dir), so removing the
package's lib/ or include/ breaks the build — L1e negative test passes with
a real dependency, not a fake one.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class DirentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Point the consumer at the package's installed CMake config.
        dep = self.dependencies["dirent"]
        tc.cache_variables["DIRENT_PACKAGE_FOLDER"] = dep.package_folder
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip consumer runtime tests")
            return
        # On HarmonyOS PC /tmp is read-only (erofs); both consumer and
        # special tests honor $TMPDIR, so point it at the build folder.
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        os.environ["TMPDIR"] = test_tmp
        os.environ["TMP"] = test_tmp
        os.environ["TEMP"] = test_tmp
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_dirent"), env="conanrun")
        self.run(os.path.join(bindir, "test_ohos_dirent"), env="conanrun")