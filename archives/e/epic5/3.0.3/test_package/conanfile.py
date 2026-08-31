#!/usr/bin/env python3
"""Conan test_package for epic5 3.0.3.

epic5 is a command-line IRC client (application, not a library).  The
smoke test builds a small C helper that invokes the installed ``epic5``
binary with ``-v`` via popen() and verifies the output contains
"EPIC5", exercising the real artifact rather than a stub (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Epic5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        # epic5 is an interactive IRC client.  The ONLY flag that makes it
        # exit after printing is -v (print version and exit).  -q means
        # "don't load .ircrc", NOT "quit after command" — any command passed
        # as a positional arg is treated as nickname/server, and the process
        # enters its infinite io("main") event loop (irc.c:1168), hanging
        # forever in headless CI.  So we never invoke epic5 interactively;
        # the regress/ ESL scripts are likewise interactive (no batch /
        # eval-and-exit mode) and their results are documented in
        # MANIFEST.yml rather than re-run here.

        pkg = self.dependencies["epic5"].package_folder
        epic5_bin = os.path.join(pkg, "bin", "epic5")

        # 1. Direct version check — the only guaranteed-clean exit path.
        self.output.info(f"Running: {epic5_bin} -v")
        self.run(f'"{epic5_bin}" -v', env="conanrun")

        # 2. Run the C smoke test via CTest.  test.c invokes epic5 -v via
        # popen() and verifies "EPIC5" in the output (R34: real artifact).
        os.environ["EPIC5_BIN"] = epic5_bin
        cmake = CMake(self)
        cmake.test()
