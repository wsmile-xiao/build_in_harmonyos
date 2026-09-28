#!/usr/bin/env python3
"""Conan test_package — libhbalinux/1.0.16 consumer verification.

Builds a consumer that uses only the installed artifacts (no source tree
access) and calls the vendor entry points exactly like libHBAAPI does:

* HBA_RegisterLibraryV2() fills the entry-point table,
* the registered handlers are then invoked (version, load, adapter count,
  adapter name lookup, adapter open, free),
* plus the OHOS-specific runtime contract: the vendor DSO must be dlopen-able
  (that is how libHBAAPI loads it via /etc/hba.conf) on a system whose
  /sys/class/fc_host tree does not exist.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibhbalinuxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libhbalinux")
        # env="conanrun" provides LD_LIBRARY_PATH for the tested package.
        self.run(binary, env="conanrun")
