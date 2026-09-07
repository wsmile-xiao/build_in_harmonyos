#!/usr/bin/env python3
"""Consumer test for pugixml public XML and XPath APIs."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PugixmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self, generator="Ninja")
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        configured = self.conf.get("tools.build:compiler_executables", default={}) or {}
        configured_c = str(configured.get("c", ""))
        configured_cxx = str(configured.get("cpp", ""))
        llvm_root = os.environ.get("OHOS_NATIVE_LLVM", "").strip()
        if llvm_root and configured_c and not os.path.isfile(configured_c):
            target = os.environ.get("OHOS_TARGET_TRIPLE", "aarch64-linux-ohos").strip()
            tc.variables["CMAKE_C_COMPILER_TARGET"] = target
            tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target
        tc.generate()
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if llvm_root and configured_c and not os.path.isfile(configured_c):
            with open(toolchain_file, encoding="utf-8") as handle:
                content = handle.read()
            content = content.replace(configured_cxx, f"{llvm_root.replace(chr(92), '/')}/clang++.exe")
            content = content.replace(configured_c, f"{llvm_root.replace(chr(92), '/')}/clang.exe")
            with open(toolchain_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built pugixml consumer cannot run on this host")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "pugixml_consumer"), env="conanrun")
