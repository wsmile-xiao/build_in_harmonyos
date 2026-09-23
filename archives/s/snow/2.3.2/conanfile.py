#!/usr/bin/env python3
"""Conan recipe for Snow 2.3.2, a header-only C testing library."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
)
from conan.tools.layout import basic_layout


class SnowConan(ConanFile):
    name = "snow"
    version = "2.3.2"
    description = "Header-only unit testing library for C"
    license = "MIT"
    homepage = "https://github.com/mortie/snow"
    url = "https://github.com/mortie/snow"
    topics = ("c", "testing", "unit-testing", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = False

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "No C compiler configured: set "
                "tools.build:compiler_executables in the Conan profile."
            )
        return cc

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler()
        test_source = os.path.join(self.source_folder, "test")
        test_build = os.path.join(self.build_folder, "upstream-tests")
        cases_build = os.path.join(test_build, "cases")
        expected_build = os.path.join(test_build, "expected")
        mkdir(self, cases_build)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "test", "expected"),
            dst=expected_build,
        )

        common_flags = (
            "-std=gnu11 -g -DSNOW_ENABLED -Wall -Wextra -Wpedantic -Werror"
        )
        include_flag = f'-I"{self.source_folder}"'

        for case_name in ("asserts", "commandline", "tests", "around"):
            source = f"cases/{case_name}.c"
            output = os.path.join(cases_build, case_name)
            self.run(
                f'"{cc}" {common_flags} -DSNOW_DUMMY_TIMER {include_flag} '
                f'"{source}" -o "{output}"',
                cwd=test_source,
            )

        harness = os.path.join(test_build, "test-snow")
        self.run(
            f'"{cc}" {common_flags} {include_flag} '
            f'"test.c" -o "{harness}"',
            cwd=test_source,
        )

        if can_run(self):
            self.run(f'"{harness}" -q', cwd=test_build)
        else:
            self.output.warning(
                "Cross-compiling: official Snow tests were compiled but cannot "
                "run on the build host"
            )

    def package(self):
        copy(
            self,
            "snow.h",
            src=os.path.join(self.source_folder, "snow"),
            dst=os.path.join(self.package_folder, "include", "snow"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "snow")
        self.cpp_info.set_property("cmake_target_name", "snow::snow")
        self.cpp_info.set_property("pkg_config_name", "snow")
