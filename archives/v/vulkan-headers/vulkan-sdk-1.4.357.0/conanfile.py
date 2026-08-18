#!/usr/bin/env python3
"""Conan recipe for vulkan-headers vulkan-sdk-1.4.357.0 — Vulkan API
header files (pure headers, CMake install, KhronosGroup source, zero deps).

Pure header-only package: CMake configure + install copies include/vulkan.
No compilation (zero deps, no config.status permission issues — unlike
autotools packages on hmdfs).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class VulkanHeadersConan(ConanFile):
    name = "vulkan-headers"
    version = "vulkan-sdk-1.4.357.0"
    description = "Vulkan API header files (KhronosGroup)"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/Vulkan-Headers"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "build-scripts"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        staging = os.path.join(self.build_folder, "vh-stage")
        # pure headers — CMake install into staging (no compilation)
        self.run(
            f"cmake -S . -B build -DCMAKE_INSTALL_PREFIX='{staging}' "
            f"-DCMAKE_INSTALL_LIBDIR=lib -DVULKAN_HEADERS_ENABLE_TESTS=OFF",
            cwd=self.source_folder)
        self.run(f"cmake --install build", cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "vh-stage")
        inc = os.path.join(staging, "include", "vulkan")
        if not os.path.isfile(os.path.join(inc, "vulkan.h")):
            raise ConanException(f"vulkan.h missing under {inc}")
        shutil.copytree(os.path.join(staging, "include"),
                        os.path.join(self.package_folder, "include"))

    def package_info(self):
        inc = os.path.join(self.package_folder, "include")
        self.output.info(f"CPATH={inc}")
