#!/usr/bin/env python3
"""Conan test_package for MultiMarkdown 6.6.0."""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MultimarkdownTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generator = "Unix Makefiles"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            # E092: CMake does not recognize OHOS, force aarch64 explicitly
            # to match the repository's existing OHOS recipes convention
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

        tc_file = Path(self.generators_folder) / "conan_toolchain.cmake"
        if tc_file.exists():
            content = tc_file.read_text(encoding="utf-8")
            content = content.replace("/data/service/hnp/bin/clang++", "clang++")
            content = content.replace("/data/service/hnp/bin/clang", "clang")
            tc_file.write_text(content, encoding="utf-8")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        dep = self.dependencies["multimarkdown"]
        mmd = os.path.join(dep.package_folder, "bin", "multimarkdown")
        source_file = os.path.join(self.build_folder, "sample.md")
        output_file = os.path.join(self.build_folder, "sample.html")
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("*hi*\n")
        self.run(f'"{mmd}" "{source_file}" > "{output_file}"', env="conanrun")
        with open(output_file, "r", encoding="utf-8") as f:
            html = f.read()
        if "<em>hi</em>" not in html:
            raise Exception(f"unexpected multimarkdown output: {html}")
        self.run(f'"{mmd}" --version', env="conanrun")
