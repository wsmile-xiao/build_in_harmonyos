#!/usr/bin/env python3
"""Consumer test for tidy/5.8.0 (library + CLI)."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TidyTestConan(ConanFile):
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
        # 1. library consumer: link libtidy and check a doc via the API
        exe = os.path.join(self.cpp.build.bindir, "test_tidy")
        self.run(f'"{exe}"', env="conanrun")
        # 2. CLI consumer: run the installed tidy binary
        script = os.path.join(self.source_folder, "test_tidy_cli.sh")
        target = os.path.join(self.build_folder, "test_tidy_cli.sh")
        shutil.copy(script, target)
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        bindir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            bindir)
        shell = self._resolve_shell()
        self.run(f'{shell} "{target}" "{bindir}"', env="conanrun")

    @staticmethod
    def _resolve_shell():
        for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/zsh",
                          "/bin/sh", "sh"):
            if os.path.isfile(candidate):
                return candidate
        return "sh"
