#!/usr/bin/env python3
"""Conan consumer test for dumb 2.0.3 — drives the packaged library the
way a downstream module player does, fully headless (no audio device):
in-memory S3M/MOD fixtures are parsed by the real loaders, the signal
renderer renders 1024 stereo samples, and the results are asserted
(failures=0)."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DumbTestConan(ConanFile):
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
        binp = os.path.join(self.cpp.build.bindirs[0], "test_dumb")
        # E077: OHOS only executes ELF files carrying a valid .codesign
        # section; remove the placeholder and self-sign before running.
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
        self.run(f'"{binp}"', env="conanrun")
