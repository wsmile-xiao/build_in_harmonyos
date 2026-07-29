#!/usr/bin/env python3
"""Conan test_package - pass-otp 1.2.0."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class PassOtpTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pass-otp"]
        extension = os.path.join(
            dep.package_folder,
            "lib",
            "password-store",
            "extensions",
            "otp.bash",
        )
        if not os.path.isfile(extension):
            raise Exception(f"Missing pass-otp extension: {extension}")

        if not can_run(self):
            self.output.info("Cross-building; file layout check completed")
            return

        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "check_pass_otp.sh")
        self.run(
            f"{shlex.quote(bash)} {shlex.quote(script)} {shlex.quote(extension)}",
            env="conanrun",
        )
