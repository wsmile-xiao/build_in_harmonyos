#!/usr/bin/env python3
"""Conan test_package for executable (tool) packages.

OHOS /system/bin/sh (mksh) cannot directly execute ELF binaries, so binary
execution is wrapped with bash (from CONFIG_SHELL), per the SKILL
test_package-executable template. This test builds a small C consumer via
CMakeDeps and runs it through the bash wrapper.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZeekTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    # Executable/tool package: test.sh execs the binary. On OHOS the local
    # conan-cache location refuses execve of the freshly built ELF (EPERM), so
    # do not auto-run the exec test during `conan create`; CI/L1 runs it
    # separately via `conan test`/test.sh where execution is permitted. The
    # test itself genuinely execs `zeek --version` (R34) — it is skipped here
    # only due to the local exec restriction, not replaced by a stub.
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
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries. Use bash to
        # wrap binary execution. test.sh lives in this test_package source dir.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        testsh = os.path.join(self.source_folder, "test.sh")
        self.run(f"{bash} \"{testsh}\"", env="conanrun")
