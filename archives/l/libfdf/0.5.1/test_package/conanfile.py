#!/usr/bin/env python3
"""Consumer test for the packaged libfdf static library and module files."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv


class LibfdfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = (
        "test_libfdf.f90",
        "test.fdf",
        "test_driver.sh",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libfdf test_package expects os=OHOS, arch=armv8"
            )

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _module_dir(self, package_folder):
        include_root = os.path.join(package_folder, "include")
        for root, _dirs, files in os.walk(include_root):
            if "fdf.mod" in files and "fdf_prec.mod" in files:
                return root
        raise ConanInvalidConfiguration(
            "packaged libfdf module files were not found under {}".format(
                include_root
            )
        )

    def test(self):
        package = self.dependencies["libfdf"].package_folder
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
        include_dir = self._module_dir(package)
        library_dir = os.path.join(package, "lib")
        script = os.path.join(self.source_folder, "test_driver.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        consumer_build = os.path.join(self.build_folder, "consumer-build")
        os.makedirs(consumer_build, exist_ok=True)

        for required in (
            flang,
            clang,
            fortran_runtime,
            fortran_decimal,
            script,
            bash,
            os.path.join(library_dir, "libfdf.a"),
        ):
            if not os.path.isfile(required):
                raise ConanInvalidConfiguration(
                    "required consumer-test input is missing: {}".format(required)
                )

        self.run(
            '"{bash}" "{script}" "{fc}" "{cc}" "{runtime}" '
            '"{decimal}" "{include}" "{lib}" "{build}" "{source}"'.format(
                bash=bash,
                script=script,
                fc=flang,
                cc=clang,
                runtime=fortran_runtime,
                decimal=fortran_decimal,
                include=include_dir,
                lib=library_dir,
                build=consumer_build,
                source=self.source_folder,
            ),
            env="conanbuild",
        )
