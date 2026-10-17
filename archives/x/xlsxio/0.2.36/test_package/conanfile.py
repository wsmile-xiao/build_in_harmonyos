#!/usr/bin/env python3
"""Consumer test for xlsxio/0.2.36 (libraries + CLI tools)."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class XlsxioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at
        # a /usr/local/lib whose incompatible libxml2.so.16 breaks the
        # SDK's lld on every link — CI-021 build #48068).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        exe = os.path.join(self.build_folder, "test_xlsxio")
        self.run(f'"{exe}"', env="conanrun")
        # CLI roundtrip against the installed tools; pass the package's
        # bin dir explicitly (PATH propagation of the tested package is
        # not relied upon).
        script = os.path.join(self.source_folder, "test_xlsxio_cli.sh")
        shell = self._resolve_shell()
        target = os.path.join(self.build_folder, "test_xlsxio_cli.sh")
        shutil.copy(script, target)
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindir
        self.run(f'{shell} "{target}" "{bindir}"', env="conanrun")

    @staticmethod
    def _resolve_shell():
        for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/zsh",
                          "/bin/sh", "sh"):
            if os.path.isfile(candidate):
                return candidate
        return "sh"
