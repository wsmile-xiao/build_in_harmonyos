import os

from conan import ConanFile


class BluezTestConan(ConanFile):
    """test_package for bluez — runs test.sh which invokes bluetoothctl --version
    (R34: 实质执行被测包二进制)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{shell} test.sh", env="conanrun")
