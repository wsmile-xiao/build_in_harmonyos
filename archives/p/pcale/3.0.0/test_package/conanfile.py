#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test package for PC-ALE (pcale) — validates library linkage and basic functionality."""

import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

class PcaleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.build_folder, self.cpp.build.bindir, "test_package")
            # OHos: /system/bin/sh (mksh) cannot execute ELF binaries directly.
            # Wrap with bash; probe multiple candidate paths for robustness (R34).
            # Start from None so a non-existent CONFIG_SHELL doesn't leave bash as
            # an invalid string that would bypass the `if not bash` guard below.
            bash = None
            cfg_shell = os.environ.get("CONFIG_SHELL")
            if cfg_shell and os.path.exists(cfg_shell):
                bash = cfg_shell
            if not bash:
                for cand in ("/data/service/hnp/bin/bash", "/system/bin/bash", "/bin/bash", "/usr/bin/bash"):
                    if os.path.exists(cand):
                        bash = cand
                        break
            if not bash:
                raise ConanException("bash not found on PATH candidates (CONFIG_SHELL, /data/service/hnp/bin/bash, /system/bin/bash, /bin/bash, /usr/bin/bash)")
            self.run(f"{bash} -c '{cmd}'", env="conanrun")
