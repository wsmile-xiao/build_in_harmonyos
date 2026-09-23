#!/usr/bin/env python3
"""Conan test package for chuffed 0.13.1.

The chuffed engine is a process-wide singleton (one problem per process, the
same way upstream fzn-chuffed runs), so each scenario is a separate binary:
  - test_package  : 6-Queens all-solutions search (4 known solutions)
  - test_optimize : maximise x under linear constraints (known optimum 6)
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _libcpp_dir(self):
        """OHOS clang links libc++_shared.so from the toolchain; the binaries
        need that directory on LD_LIBRARY_PATH at runtime."""
        cc = ""
        conf = self.conf.get("tools.build:compiler_executables")
        if conf:
            cc = str(conf.get("cpp", ""))
        if not cc:
            return ""
        cc_real = os.path.realpath(cc)
        cand = os.path.join(
            os.path.dirname(os.path.dirname(cc_real)), "lib", "aarch64-linux-ohos", "c++"
        )
        return cand if os.path.isdir(cand) else ""

    def generate(self):
        env = Environment()
        libcpp = self._libcpp_dir()
        if libcpp:
            env.prepend_path("LD_LIBRARY_PATH", libcpp)
        env.vars(self, scope="run").save_script("chuffed_libcpp_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        failures = []
        for exe in ("test_package", "test_optimize"):
            path = os.path.join(self.cpp.build.bindir, exe)
            if not os.path.isfile(path):
                raise ConanException(f"test executable not found: {path}")
            self.output.info(f"Running {exe} ...")
            self.run(f"{bash} -c '{path}'", env="conanrun")
            self.output.info(f"{exe} PASSED")
