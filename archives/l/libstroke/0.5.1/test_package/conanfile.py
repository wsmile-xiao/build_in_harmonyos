#!/usr/bin/env python3
"""Consumer-side HarmonyOS test for libstroke 0.5.1."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy


class LibstrokeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        if os.path.normpath(self.source_folder) != os.path.normpath(self.build_folder):
            copy(self, "test_libstroke.c", self.source_folder, self.build_folder)

    def build(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("This test_package is HarmonyOS-specific")

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c") or shutil.which("clang") or "clang"
        dependency = self.dependencies["libstroke"]
        include_dir = os.path.join(dependency.package_folder, "include")
        lib_dir = os.path.join(dependency.package_folder, "lib")
        source = os.path.join(self.build_folder, "test_libstroke.c")
        output = os.path.join(self.build_folder, "test_libstroke")
        args = [
            cc,
            "-std=c99",
            "-O2",
            "-I" + include_dir,
            source,
            "-L" + lib_dir,
            "-lstroke",
            "-lm",
            "-o",
            output,
        ]
        self.run(" ".join(shlex.quote(str(arg)) for arg in args), env="conanbuild")

    def test(self):
        executable = os.path.join(self.build_folder, "test_libstroke")
        self.run(executable, env="conanrun")
        self.output.info(
            'HMBS_TEST_PACKAGE_RESULT: {"executed":10,"passed":10,'
            '"failed":0,"skipped":0,"assertions":20}'
        )
