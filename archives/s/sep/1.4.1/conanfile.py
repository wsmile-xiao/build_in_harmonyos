#!/usr/bin/env python3
"""Conan recipe — SEP 1.4.1 C library (CMake)."""

import glob
import json
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0"


class SepConan(ConanFile):
    name = "sep"
    version = "1.4.1"
    description = "C library for astronomical source extraction and photometry"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/sep-developers/sep"
    url = "https://github.com/sep-developers/sep"
    topics = ("astronomy", "photometry", "source-extraction", "c")
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "SEP 1.4.1 is validated on Linux-compatible targets"
            )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.preprocessor_definitions["SEP_VERSION_STRING"] = '"{}"'.format(
            self.version
        )
        tc.generate()

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = str(executables.get("c") or "")
        if configured and (os.path.isfile(configured) or shutil.which(configured)):
            return configured

        candidates = (
            ("aarch64-unknown-linux-ohos-clang", "clang")
            if self.settings.os == "OHOS"
            else ("clang", "cc")
        )
        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration("No usable C compiler was found")

    def _run_target(self, executable, arguments):
        runner = self.conf.get(
            "user.sep:qemu_runner", default="", check_type=str
        ).strip()
        parts = [runner, shlex.quote(executable)] if runner else [shlex.quote(executable)]
        parts.extend(shlex.quote(value) for value in arguments)
        self.run(" ".join(part for part in parts if part), cwd=self.build_folder)

    def _run_upstream_c_tests(self):
        test_executable = os.path.join(self.build_folder, "sep_upstream_test_image")
        output_catalog = os.path.join(self.build_folder, "sep-test.cat")
        source_files = sorted(glob.glob(os.path.join(self.source_folder, "src", "*.c")))
        command = [
            self._c_compiler(),
            "-std=gnu11",
            "-O2",
            '-DSEP_VERSION_STRING="{}"'.format(self.version),
            "-I{}".format(os.path.join(self.source_folder, "src")),
            os.path.join(self.source_folder, "ctest", "test_image.c"),
        ]
        command.extend(source_files)
        command.extend(("-lm", "-o", test_executable))
        self.run(" ".join(shlex.quote(value) for value in command))

        self._run_target(
            test_executable,
            (os.path.join(self.source_folder, "data", "image.fits"), output_catalog),
        )
        self.run(
            "{} {} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(os.path.join(self.source_folder, "ctest", "compare.py")),
                shlex.quote(os.path.join(self.source_folder, "data", "image.cat")),
                shlex.quote(output_catalog),
            ),
            cwd=self.build_folder,
        )
        marker = {
            "status": "passed",
            "framework": "upstream C integration test",
            "command": "test_image && compare.py",
            "discovered": 2,
            "executed": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_c_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "licenses"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["sep"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "sep")
        self.cpp_info.set_property("cmake_target_name", "sep::sep")
        self.cpp_info.set_property("pkg_config_name", "sep")
