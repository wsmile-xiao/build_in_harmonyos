#!/usr/bin/env python3
"""Consumer-side test for onion: start a real HTTP server thread on
loopback and assert a full request/response roundtrip over a raw
socket."""
import os
import shlex
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class OnionTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The target loader needs an embedded path to this exact tested
            # package. Do not install into or change shared system libdirs.
            tc.cache_variables["ONION_TEST_RUNTIME_DIR"] = os.path.join(
                self.dependencies["onion"].package_folder, "lib")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-build: skipping native run (smoke binary built OK)")
            return
        self.run(shlex.quote(os.path.join(self.cpp.build.bindir, "onion_smoke")), env="conanrun")
        if str(self.settings.os) == "OHOS":
            with tempfile.TemporaryDirectory(prefix="onion-harmony-", dir=self.build_folder) as task_tmp:
                self.run(shlex.quote(os.path.join(self.cpp.build.bindir, "onion_harmony"))
                         + " " + shlex.quote(task_tmp), env="conanrun")
