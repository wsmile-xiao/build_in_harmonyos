#!/usr/bin/env python3
"""test_package for tcl 8.6.14 — validates tclsh binary and C API"""
from conan import ConanFile
import os
import sys


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

        # ----- Private header consumer test (3 assertions) -----
        # Compile against the packaged private headers (include/generic +
        # include/unix) exactly as a Tcl extension consumer (Expect) would.
        priv_inc = os.path.join(inc_dir, "generic")
        unix_inc = os.path.join(inc_dir, "unix")
        self.run(
            f'{cc} -o test_tcl_private_headers test_tcl_private_headers.c '
            f'-I"{priv_inc}" -I"{unix_inc}" -I"{inc_dir}" '
            f'-L"{lib_dir}" -ltcl8.6 -lz {rpath}',
            env="conanrun",
        )
        self.run("./test_tcl_private_headers", env="conanrun")

        # ----- tclConfig.sh consumer test (7 assertions) -----
        # Source packaged lib/tclConfig.sh with TCL_BIN_DIR preset (the exact
        # Expect configure pattern) and assert relocatability + reachability.
        self.run(f'bash test_tclconfig.sh "{pkg_folder}"', env="conanrun")

        # ----- Python consumer test (4 assertions) -----
        # Python subprocess consumer: launch the packaged tclsh8.6 directly
        # (absolute path, no system PATH / system Tcl dependency) and assert
        # patchlevel + expr output via stdin.
        self.run(f'{sys.executable} test_tcl_python.py "{tclsh}"', env="conanrun")
