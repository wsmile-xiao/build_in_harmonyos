#!/usr/bin/env python3
"""Conan test_package for smtpping (application package) — consumer E2E.

Builds a tiny mock SMTP server and then drives the packaged `smtpping` binary
against it over loopback (full banner/HELO/MAIL/RCPT/DATA/QUIT transaction),
plus CLI-contract and negative-control assertions implemented in test.sh.

`conan create` executes this automatically (CI L1a checks the trace).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SmtppingTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["smtpping"]
        smtpping_bin = os.path.join(dep.package_folder, "bin", "smtpping")
        if not os.path.exists(smtpping_bin):
            raise Exception(f"smtpping binary not found at {smtpping_bin}")
        mock = os.path.join(self.build_folder, "mock_smtp_server")
        test_script = os.path.join(self.source_folder, "test.sh")
        # OHOS: /system/bin/sh (mksh) is not used; bash runs the assertions.
        bash = os.environ.get("CONFIG_SHELL") or "bash"
        self.run(
            f'SMTPPING_BIN="{smtpping_bin}" MOCK_SMTP="{mock}" {bash} "{test_script}"',
            env="conanrun",
        )
        self.output.info("smtpping consumer E2E passed (test.sh: 15 assertions)")
