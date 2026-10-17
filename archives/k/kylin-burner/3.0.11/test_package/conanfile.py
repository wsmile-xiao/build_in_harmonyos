#!/usr/bin/env python3
"""Conan test_package for kylin-burner 3.0.11 (application).

The shipped CLI entry is `bin/burner` — an OHOS launcher that answers the
CLI query paths (--version/--help) and forwards everything else to the real
GTK3 binary (bin/burner-bin).

The test (R34, real execution — no empty shell):
  1. compiles the consumer API source test.c against the installed public
     header <burner-units.h> (installed under include/burner3, on the -I
     path; header/API surface verification);
  2. executes the packaged `bin/burner --version` launcher and asserts the
     upstream version string;
  3. verifies the real ELF binary (bin/burner-bin) and the three shared
     libraries shipped in lib/.
"""
import os
import shutil

from conan import ConanFile


class KylinburnerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        burn = self.dependencies["kylin-burner"]

        # 1) compile the consumer API source against the installed headers
        #    (burner-units.h needs glib.h — headers come from the conan deps)
        clang = shutil.which("clang") or "clang"
        glib = self.dependencies["glib"]
        include = [
            os.path.join(burn.package_folder, "include", "burner3"),
            os.path.join(glib.package_folder, "include", "glib-2.0"),
            os.path.join(glib.package_folder, "lib", "glib-2.0", "include"),
        ]
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.c")
        obj = os.path.join(self.build_folder, "test_kylin_burner.o")
        self.run(
            '"{clang}" -c "{src}" {inc} -o "{obj}"'.format(
                clang=clang, src=src,
                inc=" ".join('-I"{0}"'.format(i) for i in include), obj=obj),
            scope="build",
        )

        # 2) + 3) run the packaged launcher and verify the artifacts
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        launcher = os.path.join(burn.package_folder, "bin", "burner")
        self.run('"{bash}" "{script}" "{launcher}"'.format(bash=bash, script=script, launcher=launcher),
                 env="conanrun")
