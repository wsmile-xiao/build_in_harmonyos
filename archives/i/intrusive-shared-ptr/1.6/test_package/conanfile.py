#!/usr/bin/env python3
"""Conan consumer tests for intrusive-shared-ptr 1.6."""

import json
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class IntrusiveSharedPtrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.cache_variables["CMAKE_CXX_EXTENSIONS"] = False
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            tc.extra_cxxflags.append("-Wno-unused-command-line-argument")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        executables = (
            "test_intrusive_shared_ptr",
            "test_intrusive_shared_ptr_ohos",
        )
        needs_emulator = cross_building(self) or (
            self.settings.os == "OHOS"
            and platform.machine().lower() not in ("aarch64", "arm64")
        )
        if needs_emulator:
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS consumer tests"
                )
            for name in executables:
                executable = os.path.join(bindir, name)
                self.run(f'"{qemu}" "{executable}"', env="conanrun")
        else:
            for name in executables:
                self.run(os.path.join(bindir, name), env="conanrun")
        self._reemit_upstream_result()

    def _reemit_upstream_result(self):
        path = os.path.join(
            self.dependencies["intrusive-shared-ptr"].package_folder,
            "res",
            "hmbs_upstream.json",
        )
        with open(path, encoding="utf-8") as handle:
            result = json.load(handle)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
