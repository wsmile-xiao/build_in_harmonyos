#!/usr/bin/env python3
"""Test package for nuspell 5.1.8 - verifies the library builds and links correctly."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class NuspellTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # nuspell headers include ICU headers (unicode/locid.h etc.)
        self.requires("icu4c/77")

    def layout(self):
        cmake_layout(self)

    def _libcpp_dir(self):
        """OHOS clang links libc++_shared.so from the toolchain."""
        conf = self.conf.get("tools.build:compiler_executables")
        if conf:
            cc = str(conf.get("cpp", ""))
            if cc:
                cc_real = os.path.realpath(cc)
                cand = os.path.join(
                    os.path.dirname(os.path.dirname(cc_real)), "lib", "aarch64-linux-ohos", "c++"
                )
                return cand if os.path.isdir(cand) else ""
        return ""

    def generate(self):
        env = Environment()
        libcpp = self._libcpp_dir()
        if libcpp:
            env.prepend_path("LD_LIBRARY_PATH", libcpp)
        env.vars(self, scope="run").save_script("nuspell_libcpp_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        exe_path = os.path.join(self.cpp.build.bindir, "nuspell_test")
        assert os.path.exists(exe_path), f"Test binary not found at {exe_path}"
        self.output.info(f"Running nuspell_test ...")
        self.run(f"{bash} -c '{exe_path}'", env="conanrun")
        self.output.info("nuspell_test PASSED")
