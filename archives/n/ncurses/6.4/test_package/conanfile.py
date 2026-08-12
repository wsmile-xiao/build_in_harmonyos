#!/usr/bin/env python3
"""Consumer L1 smoke test for ncurses 6.4.

Compiles a small program that links against the packaged static wide-character
ncurses libraries and exercises terminfo + tputs, verifying the package is
usable.  Also runs ncursesw6-config --version as a metadata sanity check.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class NcursesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        # Metadata sanity: ncursesw6-config --version must report 6.4
        config = os.path.join(
            self.dependencies["ncurses"].package_folder,
            "bin",
            "ncursesw6-config",
        )
        shell = shutil.which("bash") or shutil.which("sh")
        if shell and os.path.isfile(config):
            result = subprocess.run(
                [shell, config, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0 or "6.4" not in result.stdout:
                raise ConanException(
                    f"ncursesw6-config --version failed: {result.stdout}{result.stderr}"
                )
            self.output.info(f"NCURSESW6_CONFIG_VERSION={result.stdout.strip()}")

        if not can_run(self):
            return

        # Run the compiled consumer binary that links the static libs.
        bindir = self.cpp.build.bindirs[0]
        binary = os.path.join(bindir, "test_ncurses_smoke")
        terminfo = os.path.join(
            self.dependencies["ncurses"].package_folder, "share", "terminfo"
        )
        env = os.environ.copy()
        env.update(
            {"TERM": "xterm", "TERMINFO": terminfo, "TERMINFO_DIRS": terminfo}
        )
        self.run(f'"{binary}"', env="conanrun")
