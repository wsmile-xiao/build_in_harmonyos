#!/usr/bin/env python3
"""test_package for plfit 0.9.6 — installed-package consumer verification.

Layer 1: C consumer (test.c) linked against the installed libplfit: the
packaged sampling routines generate deterministic power-law samples which
the packaged fitting routines recover, plus a version-header check.
Layer 2: CLI smoke via test.sh — the packaged plfit/plgen executables
generate and fit a sample in the conanrun environment.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class PlfitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()
        # The package is a static library, so VirtualRunEnv does not put its
        # bin/ on PATH (require.run is False for static libraries). Generate
        # an explicit run-env fragment for the CLI smoke test.
        env = Environment()
        env.prepend_path(
            "PATH",
            os.path.join(
                self.dependencies[self.tested_reference_str].package_folder,
                "bin",
            ),
        )
        env.vars(self, scope="run").save_script("plfit_runenv")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer tests run on target")
            return

        self.run(os.path.join(self.cpp.build.bindirs[0], "plfit_consumer"),
                 env="conanrun")

        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries reliably;
        # wrap the CLI smoke test with bash from the build environment.
        # Explicit cwd: test() runs from the build folder, test.sh lives in
        # the test_package source folder. The plfit_runenv fragment adds the
        # packaged bin/ to PATH (static library => not covered by conanrun).
        shell = os.environ.get("CONFIG_SHELL") or "bash"
        self.run(f'"{shell}" test.sh', cwd=self.source_folder,
                 env=["conanrun", "plfit_runenv"])
