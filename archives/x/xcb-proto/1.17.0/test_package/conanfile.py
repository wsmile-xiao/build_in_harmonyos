#!/usr/bin/env python3
"""Conan consumer tests for xcb-proto 1.17.0."""

import shlex
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


PROTOCOLS = (
    "bigreq",
    "composite",
    "damage",
    "dbe",
    "dpms",
    "dri2",
    "dri3",
    "ge",
    "glx",
    "present",
    "randr",
    "record",
    "render",
    "res",
    "screensaver",
    "shape",
    "shm",
    "sync",
    "xc_misc",
    "xevie",
    "xf86dri",
    "xf86vidmode",
    "xfixes",
    "xinerama",
    "xinput",
    "xkb",
    "xprint",
    "xproto",
    "xselinux",
    "xtest",
    "xv",
    "xvmc",
)

API_CASES = (
    "alignment-primitive",
    "alignment-offset",
    "alignment-guarantee",
    "alignment-combine",
    "alignment-log",
    "field-string",
    "expression-value",
    "expression-binary",
    "expression-unary",
    "expression-popcount",
    "expression-sumof",
    "expression-listelement",
    "expression-enumref",
    "namespace-core",
    "namespace-extension",
    "primitive-type",
    "enum-type",
    "pad-bytes",
    "pad-align",
    "doc-type",
    "module-generate",
    "module-missing-type",
)


class XcbProtoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_xcb_proto.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            raise ConanException("xcb-proto Python consumer tests must run on target")

        package = self.dependencies[self.tested_reference_str]
        package_root = Path(package.package_folder)
        script = Path(self.source_folder) / "test_xcb_proto.py"
        python = shlex.quote(sys.executable)
        script_arg = shlex.quote(str(script))
        root_arg = shlex.quote(str(package_root))
        failures = []

        def run_case(label, command):
            try:
                self.run(command, env="conanrun")
            except ConanException as error:
                failures.append(f"{label}: {error}")

        for protocol in PROTOCOLS:
            run_case(
                f"protocol:{protocol}",
                f"{python} {script_arg} protocol {shlex.quote(protocol)} {root_arg}",
            )
        for case in API_CASES:
            run_case(
                f"api:{case}",
                f"{python} {script_arg} api {shlex.quote(case)} {root_arg}",
            )
        run_case(
            "metadata:all",
            f"{python} {script_arg} metadata all {root_arg}",
        )

        if failures:
            details = "\n".join(f"- {failure}" for failure in failures)
            raise ConanException(
                f"{len(failures)} of 55 xcb-proto workflows failed:\n{details}"
            )

        self.output.info("validated 32 independent protocol generator workflows")
        self.output.info("validated 22 independent xcbgen API workflows")
        self.output.info("validated 1 installed-package metadata workflow")
