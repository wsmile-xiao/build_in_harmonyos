#!/usr/bin/env python3

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AlertmanagerIrcRelayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["alertmanager-irc-relay"].package_folder
        exe_name = (
            "alertmanager-irc-relay.exe"
            if str(self.settings.os) == "Windows"
            else "alertmanager-irc-relay"
        )
        bin_path = os.path.join(package_folder, "bin", exe_name)

        assert os.path.isfile(bin_path), (
            f"alertmanager-irc-relay binary not found: {bin_path}"
        )

        if can_run(self):
            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("sh")
                or "/bin/sh"
            )
            script = os.path.join(self.recipe_folder, "test_alertmanager_irc_relay.sh")
            self.run(
                f'"{shell}" "{script}" "{bin_path}"',
                env="conanrun",
            )
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)

            assert magic == b"\x7fELF", (
                f"alertmanager-irc-relay is not an ELF binary: {magic!r}"
            )
            self.output.info(
                f"alertmanager-irc-relay binary exists and has ELF magic: {bin_path}"
            )
