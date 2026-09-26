#!/usr/bin/env python3
"""Conan test_package for jmeters 0.4.5 (application package).

jmeters is an application (JACK + X11 level-meter GUI), so the consumer test
executes the packaged binary instead of linking a library. The binary path
is injected as JMETERS_BIN into the checker via CMakeToolchain variables.
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class JmetersTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # application package has no CMake exported target; pass the
        # packaged binary path to the checker instead.
        jmeters = self.dependencies["jmeters"]
        tc.variables["JMETERS_BIN"] = os.path.join(jmeters.package_folder, "bin", "jmeters")
        tc.generate()
        # The OHOS sandbox keeps libc++_shared.so in /system/lib64 (not in
        # any conan package folder). jmeters runs only if the GUI dynamic
        # chain also loads, so inject the system lib dir through conan's own
        # run environment (loaded in test() together with conanrun).
        if self.settings.os == "OHOS":
            env = Environment()
            env.append_path("LD_LIBRARY_PATH", "/system/lib64")
            env.vars(self).save_script("jmeters_sysenv")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        executable = Path(self.build_folder) / "test_jmeters"
        if self.settings.os == "OHOS":
            # conanrun (full transitive dep lib dirs) + jmeters_sysenv
            # (/system/lib64). Using the env list keeps BOTH the conan-run
            # paths and our system extension in the child environment.
            self.run('"{}"'.format(executable), env=["conanrun", "jmeters_sysenv"])
        else:
            self.run('"{}"'.format(executable), env="conanrun")