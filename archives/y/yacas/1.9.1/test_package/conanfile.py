#!/usr/bin/env python3
"""Consumer test for yacas/1.9.1 (library + console)."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class YacasTestConan(ConanFile):
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
        dep = self.dependencies[self.tested_reference_str]
        scripts = os.path.join(dep.package_folder, "share", "yacas",
                               "scripts")
        exe = os.path.join(self.build_folder, "test_yacas")
        self.run(f'"{exe}" "{scripts}"', env="conanrun")
        script = os.path.join(self.source_folder, "test_yacas_cli.sh")
        target = os.path.join(self.build_folder, "test_yacas_cli.sh")
        shutil.copy(script, target)
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindir
        sharedir = os.path.join(dep.package_folder, "share")
        shell = self._resolve_shell()
        self.run(f'{shell} "{target}" "{bindir}" "{sharedir}"',
                 env="conanrun")

    @staticmethod
    def _resolve_shell():
        for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/zsh",
                          "/bin/sh", "sh"):
            if os.path.isfile(candidate):
                return candidate
        return "sh"
