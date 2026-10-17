#!/usr/bin/env python3
"""Consumer verification for the installed TECkit package."""

import base64
import os
import shlex

from conan import ConanFile


class TeckitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _absolute(base, path):
        return path if os.path.isabs(path) else os.path.join(base, path)

    def _prepare_tmpdir(self):
        # HarmonyOS mounts '/' and '/tmp' read-only, so the compiler cannot
        # create its temporary files there.  Keep them inside the test package
        # folders, which are writable on the device.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            os.environ[name] = tmpdir
        return tmpdir

    def _mapping_path(self):
        # Keep the upstream compiled mapping in the GitCode PR as base64 text;
        # binary files make the platform's PR diff unappliable in CI.
        encoded = os.path.join(
            self.source_folder, "upstream_test", "academy.tec.b64"
        )
        decoded = os.path.join(self.build_folder, "academy.tec")
        os.makedirs(self.build_folder, exist_ok=True)
        with open(encoded, "rb") as source, open(decoded, "wb") as target:
            base64.decode(source, target)
        return decoded

    def build(self):
        self._prepare_tmpdir()
        dependency = self.dependencies["teckit"]
        compilers = (
            self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            or {}
        )
        cxx = str(compilers.get("cpp") or "clang++")

        include_dirs = [
            self._absolute(dependency.package_folder, path)
            for path in dependency.cpp_info.includedirs
        ]
        library_dirs = [
            self._absolute(dependency.package_folder, path)
            for path in dependency.cpp_info.libdirs
        ]

        command = [
            cxx,
            "-std=c++11",
            "-O1",
            "-Wall",
            "-Wextra",
            os.path.join(self.source_folder, "consumer.cpp"),
            "-o",
            os.path.join(self.build_folder, "consumer"),
        ]
        command.extend("-I" + path for path in include_dirs)
        command.extend("-L" + path for path in library_dirs)
        command.extend(["-lTECkit_Compiler", "-lTECkit"])
        self.run(" ".join(shlex.quote(item) for item in command), env="conanbuild")

    def test(self):
        self._prepare_tmpdir()
        self.run(
            "%s %s"
            % (
                shlex.quote(os.path.join(self.build_folder, "consumer")),
                shlex.quote(self._mapping_path()),
            ),
            env="conanrun",
        )
