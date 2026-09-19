#!/usr/bin/env python3
"""test_package for handy 0.2.0 — a consumer that exercises the library."""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class HandyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (CI worker precedent: an
        # incompatible libxml2.so.16 in /usr/local/lib breaks the SDK lld).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "handy_consumer_test")
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if str(self.settings.os) == "OHOS":
            self._sign(exe)
            environment = Environment()
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            with environment.vars(self).apply():
                self.run(exe, env="conanrun")
        else:
            self.run(exe, env="conanrun")

    def _sign(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"signing tool missing: {tool}")
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)
