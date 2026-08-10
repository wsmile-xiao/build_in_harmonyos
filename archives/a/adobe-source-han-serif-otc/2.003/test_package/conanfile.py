#!/usr/bin/env python3
"""Consumer test for adobe-source-han-serif-otc/2.003."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AdobeSourceHanSerifOtcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["adobe-source-han-serif-otc"]
        font_root = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0])
        font_count = sum(
            filename.lower().endswith(".ttc")
            for _, _, filenames in os.walk(font_root)
            for filename in filenames
        )
        if font_count != 7:
            raise ConanException(
                f"Expected 7 packaged OpenType collections, found {font_count}"
            )
        if not can_run(self):
            self.output.info("Cross-built font_probe; runtime is verified on the OHOS emulator")
            return
        probe = os.path.join(self.cpp.build.bindir, "font_probe")
        self.run(f'"{probe}" "{font_root}" 7 5', env="conanrun")
        corrupt = os.path.join(self.source_folder, "corrupt.ttc")
        self.run(f'"{probe}" --expect-invalid "{corrupt}"', env="conanrun")
