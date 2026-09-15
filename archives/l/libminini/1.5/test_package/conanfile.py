#!/usr/bin/env python3
"""Consumer tests for libminini 1.5 on OHOS."""

import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.layout import basic_layout


class LibmininiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "*.c", "*.cpp"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _tool(self, key, ohos_name, native_names):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = str(executables.get(key) or "")
        if configured and (os.path.isfile(configured) or shutil.which(configured)):
            return configured
        candidates = [ohos_name] if self.settings.os == "OHOS" else list(native_names)
        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration("No usable {} compiler".format(key))

    def _compile(self, compiler, standard, source, output):
        dependency = self.dependencies[self.tested_reference_str]
        include_dir = dependency.cpp_info.includedirs[0]
        lib_dir = dependency.cpp_info.libdirs[0]
        command = "{} -std={} -I{} {} -L{} -lminini -o {}".format(
            shlex.quote(compiler), standard, shlex.quote(include_dir),
            shlex.quote(os.path.join(self.source_folder, source)),
            shlex.quote(lib_dir), shlex.quote(output)
        )
        self.run(command)

    def build(self):
        cc = self._tool("c", "aarch64-unknown-linux-ohos-clang", ("clang", "cc"))
        cxx = self._tool(
            "cpp", "aarch64-unknown-linux-ohos-clang++", ("clang++", "c++")
        )
        self._compile(cc, "c99", "test_c.c",
                      os.path.join(self.build_folder, "test_c"))
        self._compile(cxx, "c++17", "test_cpp.cpp",
                      os.path.join(self.build_folder, "test_cpp"))
        self._compile(cc, "c99", "harmonyos_specific_test.c",
                      os.path.join(self.build_folder, "harmonyos_specific_test"))

    def _run_test(self, name):
        executable = os.path.join(self.build_folder, name)
        runner = self.conf.get(
            "user.libminini:qemu_runner", default="", check_type=str
        ).strip()
        command = "{} {}".format(runner, shlex.quote(executable)).strip()
        self.run(command, cwd=self.build_folder)

    def test(self):
        self._run_test("test_c")
        self._run_test("test_cpp")
        self._run_test("harmonyos_specific_test")
        marker = {
            "executed": True,
            "passed": True,
            "command": "test_c && test_cpp && harmonyos_specific_test",
            "discovered": 3,
            "passedCount": 3,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
