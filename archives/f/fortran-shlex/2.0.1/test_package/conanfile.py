#!/usr/bin/env python3
"""Consumer test for the packaged fortran-shlex module and static library."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv


class FortranShlexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_fortran_shlex.f90", "test_driver.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def test(self):
        package = self.dependencies["fortran-shlex"].package_folder
        flang_package = self.dependencies.build["flang-ohos"].package_folder

        flang = os.path.join(flang_package, "bin", "flang")
        fortran_runtime = os.path.join(
            flang_package, "lib", "libFortranRuntime.a"
        )
        fortran_decimal = os.path.join(
            flang_package, "lib", "libFortranDecimal.a"
        )
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        clang = compilers.get("c", "/data/service/hnp/bin/clang")
        include_dir = os.path.join(package, "include")
        library_dir = os.path.join(package, "lib")
        script = os.path.join(self.source_folder, "test_driver.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        for required in (
            flang,
            clang,
            fortran_runtime,
            fortran_decimal,
            script,
            bash,
        ):
            if not os.path.isfile(required):
                raise ConanInvalidConfiguration(
                    "required consumer-test input is missing: {}".format(required)
                )

        self.run(
            '"{bash}" "{script}" "{fc}" "{cc}" "{runtime}" "{decimal}" '
            '"{inc}" "{lib}" "{build}"'.format(
                bash=bash,
                script=script,
                fc=flang,
                cc=clang,
                runtime=fortran_runtime,
                decimal=fortran_decimal,
                inc=include_dir,
                lib=library_dir,
                build=self.build_folder,
            ),
            env="conanbuild",
        )
