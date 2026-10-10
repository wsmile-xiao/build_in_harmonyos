#!/usr/bin/env python3
"""Conan test package — ratpoints public API, CLI, and OHOS ABI checks."""

import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class RatpointsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test_ratpoints.c"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = (compilers.get("c") or "").strip()
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def build(self):
        ratpoints = self.dependencies["ratpoints"]
        gmp = self.dependencies["gmp"]
        args = [
            self._compiler(),
            "-Wall",
            "-Wextra",
            os.path.join(self.source_folder, "test_ratpoints.c"),
            "-o",
            os.path.join(self.build_folder, "test_ratpoints"),
        ]
        for dependency in (ratpoints, gmp):
            args.extend("-I" + path for path in dependency.cpp_info.includedirs)
        for dependency in (ratpoints, gmp):
            args.extend("-L" + path for path in dependency.cpp_info.libdirs)
        args.extend(("-lratpoints", "-lgmp"))
        args.append("-lm")
        self.run(shlex.join(args))

    def test(self):
        if not can_run(self):
            raise ConanException("ratpoints consumer tests must run natively")

        test_binary = os.path.join(self.build_folder, "test_ratpoints")
        self.run(shlex.quote(test_binary), env="conanrun")

        cli_output = os.path.join(self.build_folder, "ratpoints-cli.out")
        cli = os.path.join(
            self.dependencies["ratpoints"].cpp_info.bindirs[0], "ratpoints"
        )
        self.run(
            "%s '-1 0 1' 10 > %s" %
            (shlex.quote(cli), shlex.quote(cli_output)),
            env="conanrun",
        )
        with open(cli_output, encoding="utf-8") as output_file:
            output = output_file.read()
        expected_fragments = (
            "Curve equation is  y^2 = x^2 - 1",
            "(1 : 0 : 1)",
            "12 rational points found.",
        )
        missing = [fragment for fragment in expected_fragments if fragment not in output]
        if missing:
            raise ConanException(
                "Installed ratpoints CLI output is missing: %s" % missing
            )

        assertions = 13 if str(self.settings.os) == "OHOS" else 11
        marker = {
            "executed": True,
            "passed": True,
            "command": "test_ratpoints + installed ratpoints CLI",
            "discovered": assertions,
            "passedCount": assertions,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
