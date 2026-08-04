#!/usr/bin/env python3
"""Run NSD version, configuration, and zone validation checks."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NsdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        bindir = os.path.join(self.dependencies["nsd"].package_folder, "bin")
        zone = os.path.join(self.source_folder, "example.test.zone")
        config = os.path.join(self.build_folder, "nsd.conf")

        with open(config, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(
                "server:\n"
                "  ip-address: 127.0.0.1\n"
                "  port: 5353\n"
                "  database: \"\"\n"
                "zone:\n"
                "  name: example.test\n"
                f'  zonefile: "{zone}"\n'
            )

        script = os.path.join(self.source_folder, "test_nsd.sh")
        self.run(
            f'sh "{script}" "{bindir}" "{config}" "{zone}"',
            env="conanrun",
        )
