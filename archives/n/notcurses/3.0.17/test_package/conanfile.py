#!/usr/bin/env python3
"""Conan test_package — notcurses 3.0.17 (Conan L1 official test).

Two-part verification (R34/R40):
1. notcurses_version() API + version string check
2. pty-based functional cycle: init → render → injected keypress → stop
   (verifies the OHOS adaptation end-to-end: query handling with bounded
   waits, cooperative input-thread shutdown, no deadlocks)

File location: archives/n/notcurses/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class NotcursesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # direct require: notcurses_init() needs a terminfo database; the
        # ncurses package bundles one (static transitive deps are pruned
        # from the consumer graph, so request it explicitly)
        self.requires("ncurses/6.4")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # notcurses_init() needs a terminfo entry for TERM. The ncurses
        # package bundles one; point TERMINFO at it so the pty test can run
        # headlessly (no system terminfo database on CI workers).
        # Named conanrun* so self.run(..., env="conanrun") sources it.
        nc = self.dependencies.get("ncurses")
        if nc:
            for sub in ("lib/terminfo", "share/terminfo"):
                cand = os.path.join(nc.package_folder, sub)
                if os.path.isdir(cand):
                    env = Environment()
                    env.define("TERMINFO", cand)
                    env.vars(self, scope="run").save_script("conanrunterminfo")
                    break

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # E298: explicit self.run() with env="conanrun" ensures the Conan
        # runtime environment (LD_LIBRARY_PATH + TERMINFO) is activated.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_notcurses")
        self.run(exe, env="conanrun")
