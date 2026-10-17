#!/usr/bin/env python3
"""Conan consumer test for TetGen 1.6.0.

The real-machine shadow-CI environment does not expose ``cmake`` on PATH, so this
test_package compiles the consumer executable directly with the HarmonyOS clang++
resolved from ``tools.build:compiler_executables`` (a dict, see the main recipe's
R33 note) instead of relying on the CMake build helper.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.layout import basic_layout


class TetgenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # tools.build:compiler_executables is a single dict-valued conf; read the
        # whole value and index it (the ``:cpp`` subkey form raises on conan 2.30).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or "/data/service/hnp/bin/clang++"

        dep = self.dependencies["tetgen"]
        incdir = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])

        src = os.path.join(self.source_folder, "test_tetgen.cpp")
        exe = os.path.join(self.build_folder, "test_tetgen")

        self.run(
            f'"{cxx}" -std=c++11 -I"{incdir}" "{src}" '
            f'-L"{libdir}" -ltet -lm -o "{exe}"'
        )
        self._sign(exe)

    def test(self):
        exe = os.path.join(self.build_folder, "test_tetgen")
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" -c \'{exe}\'', env="conanrun")

    @staticmethod
    def _sign(executable):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute tests on OHOS"
            )
        signed = executable + ".signed"
        if os.path.isfile(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", executable],
                check=False,
            )
        subprocess.run(
            [signer, "sign", "-inFile", executable, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
