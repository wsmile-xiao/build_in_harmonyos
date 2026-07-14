#!/usr/bin/env python3
"""Conan test_package — nudoku 5.0.4.

Calls the real solver API by compiling test.c against the installed libnudoku.a,
then smoke-tests the installed nudoku binary.
"""
import os

from conan import ConanFile


class NudokuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: only meaningful on Linux/OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg = self.dependencies["nudoku"].package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        nudoku_bin = os.path.join(pkg, "bin", "nudoku")

        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")

        # 1) Compile the solver-API test against the installed libnudoku.a.
        self.run(f"{cc} test.c -I{inc} -L{lib} -lnudoku -o test")
        # 2) Run it (exits 0 iff all solver assertions pass).
        self.run("./test", env="conanrun")

        # 3) Smoke-test the installed binary: nudoku -v exits 0 with version.
        assert os.path.isfile(nudoku_bin), f"nudoku binary missing: {nudoku_bin}"
        self.run(f'"{nudoku_bin}" -v | grep -q "nudoku version"')
