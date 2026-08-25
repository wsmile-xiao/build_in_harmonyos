#!/usr/bin/env python3
"""Conan test_package for libscfg 0.2.0 — Conan L1 official test.

Uses CMake (CMakeDeps + CMakeToolchain) so the compiler is handled by the
Conan toolchain, not raw shell env vars. The test program calls libscfg's
real API (scfg_parse_file / scfg_format_file / scfg_block_finish) to
verify parsing, structure access, round-trip formatting, and cleanup.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibscfgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()
        # Generate LD_LIBRARY_PATH for shared library runtime
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries.
        # Use bash to wrap binary execution (OHOS has no /bin/sh).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.exists(bash):
            # fallback: bash from PATH (non-OHOS / dev hosts)
            import shutil
            bash = shutil.which("bash") or "bash"
        # Set LD_LIBRARY_PATH for shared library runtime
        lib_dir = os.path.join(self.dependencies["libscfg"].package_folder, "lib")
        self.run(f'LD_LIBRARY_PATH={lib_dir} {bash} -c "./test_scfg"')
