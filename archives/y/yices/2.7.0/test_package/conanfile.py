#!/usr/bin/env python3
"""Consumer test for yices/2.7.0 (library + CLI tools)."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class YicesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (lld/libxml2 shield).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        exe = os.path.join(self.build_folder, "test_yices")
        self.run(f'"{exe}"', env="conanrun")
        script = os.path.join(self.source_folder, "test_yices_cli.sh")
        target = os.path.join(self.build_folder, "test_yices_cli.sh")
        shutil.copy(script, target)
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindir
        shell = self._resolve_shell()
        self.run(f'{shell} "{target}" "{bindir}"', env="conanrun")

    @staticmethod
    def _resolve_shell():
        for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/zsh",
                          "/bin/sh", "sh"):
            if os.path.isfile(candidate):
                return candidate
        return "sh"
