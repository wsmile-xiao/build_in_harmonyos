#!/usr/bin/env python3
"""Conan recipe for matrix_hub 2.0 — a lightweight C matrix computation
and LP/MIP optimization toolkit (header-only library + CLI tools)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MatrixHubConan(ConanFile):
    name = "matrix_hub"
    version = "2.0"
    description = "Lightweight C matrix computation and LP/MIP optimization toolkit"
    license = "Apache-2.0"
    homepage = "https://github.com/Amoiensis/Matrix_hub"
    url = "https://github.com/Amoiensis/Matrix_hub"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Header-only INTERFACE 库 + CLI 工具混合形态：shared 仅影响工具链
    # BUILD_SHARED_LIBS 开关（无 .so/.a 库产物），默认关闭即可。
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake has no OHOS platform module; the package is C99-only and does
        # not rely on Linux-specific APIs, so build natively with clang.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        # header-only INTERFACE 库：无可链接库文件，libs 保持为空（避免消费者误链接）。
        self.cpp_info.libs = []
        # Ship the CLI tools on PATH so consumers' run environments (and the
        # test_package's conanrun step) can invoke Matrix_Hub_v2_0_cli/solver.
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))