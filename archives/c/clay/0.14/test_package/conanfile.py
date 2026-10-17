#!/usr/bin/env python3
"""Conan consumer test for clay 0.14 — drives the packaged static library
the way a downstream project does:
1. compile the consumer layout-assertion program with the packaged
   libclay.a + clay.h (declaration-only include) via CMake
   (clay::clay target);
2. execute the signed binary (E077): it builds two real layouts
   (flex sidebar/content with fixed-width verification, clipped
   scrolling container with scissor-pair verification) and asserts on
   the generated Clay_RenderCommandArray (8 checks, failures=0)."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ClayTestConan(ConanFile):
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
        binp = os.path.join(self.cpp.build.bindirs[0], "test_clay")
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
