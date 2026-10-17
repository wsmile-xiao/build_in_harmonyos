#!/usr/bin/env python3
"""Consumer-side test for tomlc99: parse an inline TOML document and
assert typed accessors plus nested-table lookup."""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class Tomlc99TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise RuntimeError("Consumer and Harmony tests require target execution")
        binary = os.path.abspath(os.path.join(self.cpp.build.bindir, "tomlc99_smoke"))
        if self.settings.os == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise RuntimeError("Native binary-sign-tool is required")
            private = os.path.join(self.build_folder, "harmony-private")
            os.makedirs(private, exist_ok=False)
            for name in ("tomlc99_smoke", "tomlc99_harmony"):
                exe = os.path.abspath(os.path.join(self.cpp.build.bindir, name))
                subprocess.run([signer, "sign", "-selfSign", "1", "-inFile", exe,
                                "-outFile", exe + ".signed"], check=True, timeout=30)
                os.chmod(exe + ".signed", 0o700)
            self.run(shlex.join([binary + ".signed"]), env="conanrun")
            harmony = os.path.abspath(os.path.join(self.cpp.build.bindir, "tomlc99_harmony.signed"))
            self.run(shlex.join([harmony, private]), env="conanrun")
        else:
            self.run('"' + binary + '"', env="conanrun")
