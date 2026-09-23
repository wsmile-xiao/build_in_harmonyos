#!/usr/bin/env python3
"""Conan consumer test for cek 0.2.0."""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CekTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["cek"]
        executable = "cek.exe" if str(self.settings.os) == "Windows" else "cek"
        binary = os.path.join(package.package_folder, "bin", executable)
        if not os.path.isfile(binary):
            raise ConanException(f"packaged cek binary not found: {binary}")

        if can_run(self):
            shell = os.environ.get("SHELL", "/bin/sh")
            script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'"{shell}" "{script}" "{binary}"', env="conanrun")
        else:
            with open(binary, "rb") as stream:
                magic = stream.read(4)
            if magic != b"\x7fELF":
                raise ConanException(f"cek is not an ELF binary: {magic!r}")
            self.output.info(f"cek binary exists and has ELF magic: {binary}")

        result_file = os.path.join(package.package_folder, "res", "upstream_test_result.json")
        if os.path.isfile(result_file):
            with open(result_file, "r", encoding="utf-8") as stream:
                result = json.load(stream)
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(result, separators=(",", ":"), ensure_ascii=False)
            )
