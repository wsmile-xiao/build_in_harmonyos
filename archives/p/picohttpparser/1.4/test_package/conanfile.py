#!/usr/bin/env python3
"""Conan test_package for picohttpparser 1.4 — Conan L1 consumer test.

Builds test.c against the packaged library (CMakeDeps resolves
picohttpparser::picohttpparser) and runs it. test.c only uses the public API
declared in picohttpparser.h, so the test cannot pass when the package is
missing or its headers/library are stale (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

# OHOS: /system/bin/sh (mksh) may fail to exec an ELF file directly; wrap in bash.
_SHELL_FALLBACK = "/data/service/hnp/bin/bash"


class PicohttpparserTestConan(ConanFile):
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
        shell = os.environ.get("CONFIG_SHELL", _SHELL_FALLBACK)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_picohttpparser")
        # `bash -c '<binary>'` execs the ELF; passing the binary as bash's
        # argument would make bash interpret it as a shell script instead.
        self.run(f"{shell} -c '\"{exe}\"'", env="conanrun")
