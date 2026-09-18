#!/usr/bin/env python3
"""Conan test_package — libmediainfo consumer-side functional test.

Builds test.cpp against the installed libmediainfo package and runs it on
the OHOS device: the binary parses the official MediaArea Example.ogg
regression sample (embedded base64) through the full MediaInfo pipeline
and asserts container/audio/format/bitrate-mode/Unicode-tag/XML-output
metadata.  See test.cpp for the assertion list.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibmediainfoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # ZenLib 0.4.41 asks for CMake 3.1; CMake >= 4 needs the policy floor.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: run via the build shell (CONFIG_SHELL) like avimetaedit,
        # with TMPDIR pointing at the writable sandbox cache so the test
        # can write its sample file.  The test binary links libc++
        # dynamically: the OHOS SDK aarch64 libc++_shared.so must be on
        # LD_LIBRARY_PATH (the conanrun env of a static package does not
        # carry it).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        tmp = os.environ.get("TMPDIR") or "/data/storage/el2/base/cache"
        libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        # The binary falls back to TMPDIR when argv[1] is absent; pass an
        # explicit path under TMPDIR for environments where /tmp is absent.
        self.run(f"{bash} -c 'TMPDIR={tmp} LD_LIBRARY_PATH={libcxx} "
                 f"./mediainfo_test {tmp}/mi_tp_example.ogg'",
                 env="conanrun")
