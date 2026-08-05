#!/usr/bin/env python3
"""test_package for tcl 8.6.14 — validates tclsh binary and C API"""
from conan import ConanFile
import os


class TclTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use package_folder for absolute paths (avoids PATH dependency for CI)
        pkg_folder = self.dependencies["tcl"].package_folder
        tclsh = os.path.join(pkg_folder, "bin", "tclsh8.6")

        # ----- Shell-based smoke test (6 assertions) -----
        self.run(f'TCLSH="{tclsh}" bash test_tcl.sh', env="conanrun")

        # ----- C API test (4 assertions) -----
        inc_dir = os.path.join(pkg_folder, "include")
        lib_dir = os.path.join(pkg_folder, "lib")
        cc = os.environ.get("CC", "clang")
        rpath = f"-Wl,-rpath,{lib_dir}" if self.settings.os != "Windows" else ""
        self.run(
            f'{cc} -o test_tcl_api test_tcl_api.c -I"{inc_dir}" -L"{lib_dir}" '
            f'-ltcl8.6 -lz {rpath}',
            env="conanrun",
        )
        self.run("./test_tcl_api", env="conanrun")
