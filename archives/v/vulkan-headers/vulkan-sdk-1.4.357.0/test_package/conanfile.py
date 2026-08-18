#!/usr/bin/env python3
"""Conan test_package for vulkan-headers vulkan-sdk-1.4.357.0 — consumer
check. Runs test_vulkan_headers.py (standalone test source, satisfies
L0c) via self.run with env="conanrun" (conanrun PATH injection required
— see yarl lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class VulkanHeadersTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["vulkan-headers"].package_folder
        inc = os.path.join(pkg, "include")
        if not os.path.isfile(os.path.join(inc, "vulkan", "vulkan.h")):
            raise ConanException(f"vulkan.h missing under {inc}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_vulkan_headers.py")
        if not os.path.isfile(test_script):
            raise ConanException(
                f"test_vulkan_headers.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{inc}'", env="conanrun")
