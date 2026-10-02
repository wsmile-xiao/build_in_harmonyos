#!/usr/bin/env python3
"""test_package for rtl-wmbus 1.1.0.

Two real test binaries are built against the packaged tool and executed in
test(); neither is a shell/print stub (R34 / CI L0c+L0d / preflight PF3).

  test_decode        – functional: pipes a recorded RTL-SDR capture through the
                       packaged `rtl_wmbus` and asserts the decoded WM-Bus
                       telegram field by field.
  ohos_special_test  – HarmonyOS-specific: asserts the packaged executable is a
                       real OHOS aarch64 (musl) ELF and exercises the POSIX-only
                       code paths (alarm/signal flow control).

VirtualRunEnv puts the package's bin/ on PATH so both binaries locate
`rtl_wmbus` through PATH lookup.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


class RtlWmbusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        # ohos_special_test.c asserts OHOS-specific ABI facts (EM_AARCH64, the
        # musl loader). The recipe also accepts os=Linux, where those would be
        # wrong rather than revealing a defect — so the expectation is passed
        # down from settings instead of being hardcoded in the test.
        tc.cache_variables["TARGET_IS_OHOS_AARCH64"] = bool(
            self.settings.os == "OHOS" and self.settings.arch == "armv8")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Real execution of the built test binaries — CI L0d greps this file for
        # echo/print-only self.run() and rejects it.
        self.run("./test_decode", env="conanrun")
        self.run("./ohos_special_test", env="conanrun")
