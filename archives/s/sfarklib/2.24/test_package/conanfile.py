#!/usr/bin/env python3
"""OHOS consumer test for sfArkLib 2.24."""

import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.layout import basic_layout


class SfarklibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test_sfarklib.cpp"
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
        raise ConanInvalidConfiguration("No usable C++ compiler was found")

    def _dependency(self, name):
        for dependency in self.dependencies.host.values():
            if dependency.ref and dependency.ref.name == name:
                return dependency
        raise ConanInvalidConfiguration("Missing dependency: {}".format(name))

    def build(self):
        cxx = self._tool(
            "cpp", "aarch64-unknown-linux-ohos-clang++", ("clang++", "c++")
        )
        sfarklib = self._dependency("sfarklib")
        zlib = self._dependency("zlib")
        include_flags = " ".join(
            "-I{}".format(shlex.quote(path))
            for dependency in (sfarklib, zlib)
            for path in dependency.cpp_info.includedirs
        )
        sfark_archive = os.path.join(sfarklib.cpp_info.libdirs[0], "libsfark.a")
        zlib_archive = os.path.join(zlib.cpp_info.libdirs[0], "libz.a")
        executable = os.path.join(self.build_folder, "test_sfarklib")
        source = os.path.join(self.source_folder, "test_sfarklib.cpp")
        self.run(
            "{} -std=c++17 -static-libstdc++ {} {} {} {} -lm -o {}".format(
                shlex.quote(cxx),
                include_flags,
                shlex.quote(source),
                shlex.quote(sfark_archive),
                shlex.quote(zlib_archive),
                shlex.quote(executable),
            )
        )

    def test(self):
        executable = os.path.join(self.build_folder, "test_sfarklib")
        runner = self.conf.get(
            "user.sfarklib:qemu_runner", default="", check_type=str
        ).strip()
        command = "{} {}".format(runner, shlex.quote(executable)).strip()
        self.run(command, cwd=self.build_folder)
        marker = {
            "executed": True,
            "passed": True,
            "command": "test_sfarklib",
            "discovered": 1,
            "passedCount": 1,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
