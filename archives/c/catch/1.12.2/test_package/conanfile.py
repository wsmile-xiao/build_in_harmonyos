#!/usr/bin/env python3
"""Conan consumer test for catch 1.12.2 — builds a real TEST_CASE program
with CMake, signs the executable for OHOS execution (E077) and asserts the
Catch runner reports success."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CatchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        binp = os.path.join(self.cpp.build.bindirs[0], "test_catch")
        # E077: OHOS only executes ELF files carrying a valid .codesign
        # section; a freshly built binary holds an unsigned placeholder that
        # must be removed before self-signing. On hosts without the signing
        # tools the binary runs unsigned (best effort, matches upstream use).
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(signer) and os.path.isfile(objcopy):
            signer_env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binp],
                capture_output=True, timeout=60, env=signer_env,
            )
            signed = binp + ".signed"
            subprocess.run(
                [signer, "sign", "-inFile", binp, "-outFile", signed, "-selfSign", "1"],
                check=True, timeout=60, env=signer_env,
            )
            os.replace(signed, binp)
        os.chmod(binp, 0o755)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_check.sh")
        self.run(f'{bash} "{script}" "{binp}"', env="conanrun")
