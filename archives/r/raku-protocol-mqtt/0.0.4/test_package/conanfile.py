#!/usr/bin/env python3
"""Consumer test for Protocol::MQTT 0.0.4."""

import os

from conan import ConanFile


class RakuProtocolMqttTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_mqtt.raku", "test_mqtt.py"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        runner = os.path.join(self.source_folder, "test_mqtt.py")
        script = os.path.join(self.source_folder, "test_mqtt.raku")
        raku = os.path.join(self.dependencies["rakudo"].package_folder, "bin", "raku")
        self.run(f'python3 "{runner}" "{raku}" "{script}"', env="conanrun")
