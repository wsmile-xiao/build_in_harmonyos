#!/usr/bin/env python3
"""Conan test_package — libtecla 1.6.3 (Tecla command-line editing library).

L1 official test: verifies the packaged static library is usable.
The test script:
  - checks include/libtecla.h and lib/libtecla.a exist
  - compiles a C program against the packaged header + static lib and runs
    it, asserting libtecla_version() reports 1.6.3 (R34: substantively
    calls the packaged library API)
"""
import os
from pathlib import Path

from conan import ConanFile


class LibteclaTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Resolve the C compiler from the toolchain conf (OHOS clang) and
        # export it as CC for the test script; gcc is not available on OHOS.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        os.environ["CC"] = cc

        # Locate the libtecla package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("libtecla")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get libtecla package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_libtecla.sh"
        if pkg_root:
            os.environ["LIBTECLA_PKG_ROOT"] = str(pkg_root)
        self.run(f'sh {test_script}')
