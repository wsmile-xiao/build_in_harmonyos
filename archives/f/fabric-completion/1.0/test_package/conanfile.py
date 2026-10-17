#!/usr/bin/env python3
"""Consumer test for fabric-completion/1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FabricCompletionTestConan(ConanFile):
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
        dep = self.dependencies["fabric-completion"]
        # 探针需要 completions 与 doc 两个目录，传包根由探针自行定位
        # （resdirs 只暴露 completions，README 在 share/doc/ 下）。
        root = dep.package_folder
        completions = os.path.join(root, dep.cpp_info.resdirs[0])
        if not os.path.isdir(completions):
            raise Exception(f"fabric-completion completions dir not found: {completions}")
        if not can_run(self):
            self.output.info("Cross-built fabric_completion_probe; runtime "
                             "verification is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "fabric_completion_probe")
        self.run(f'"{probe}" "{root}"', env="conanrun")
