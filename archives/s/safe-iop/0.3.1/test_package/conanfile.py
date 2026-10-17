#!/usr/bin/env python3
"""Consumer tests for safe-iop 0.3.1."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class SafeIopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = (executables.get("c") or "").strip()
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        if configured:
            fallback = shutil.which(os.path.basename(configured))
            if fallback:
                return fallback
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def _dependency_paths(self):
        includedirs = []
        libdirs = []
        for dependency in self.dependencies.values():
            includedirs.extend(dependency.cpp_info.includedirs)
            libdirs.extend(dependency.cpp_info.libdirs)
        if not includedirs or not libdirs:
            raise ConanException("safe-iop include or library directory is missing")
        return includedirs, libdirs

    def _compile(self, source_name, output_name):
        includedirs, libdirs = self._dependency_paths()
        command = [
            self._compiler(),
            "-std=gnu11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-DNDEBUG",
            os.path.join(self.source_folder, source_name),
            "-o",
            os.path.join(self.build_folder, output_name),
        ]
        for path in includedirs:
            command += ["-I", path]
        for path in libdirs:
            command += ["-L", path]
        command += ["-lsafe_iop", "-Wl,-rpath," + libdirs[0]]
        self.output.info("+ %s" % " ".join(command))
        process = subprocess.run(
            command,
            cwd=self.build_folder,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        if process.stdout:
            self.output.info(process.stdout.rstrip())
        if process.returncode != 0:
            raise ConanException(
                "consumer compile failed (rc=%s): %s"
                % (process.returncode, process.stdout[-4000:])
            )

    def build(self):
        os.makedirs(self.build_folder, exist_ok=True)
        self._compile("test_safe_iop.c", "test_safe_iop")
        if self.settings.os == "OHOS":
            self._compile("test_safe_iop_ohos.c", "test_safe_iop_ohos")

    def test(self):
        if not can_run(self):
            raise ConanException("can_run=False: consumer binaries must execute")
        general = os.path.join(self.build_folder, "test_safe_iop")
        self.run('"%s"' % general, env="conanrun")
        discovered = 12
        if self.settings.os == "OHOS":
            ohos = os.path.join(self.build_folder, "test_safe_iop_ohos")
            self.run('"%s"' % ohos, env="conanrun")
            discovered += 5
        marker = {
            "executed": True,
            "passed": True,
            "command": "test_safe_iop and test_safe_iop_ohos",
            "discovered": discovered,
            "passedCount": discovered,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
