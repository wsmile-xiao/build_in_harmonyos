import os

from conan import ConanFile


class SNailTestConan(ConanFile):
    """test_package for s-nail -- runs test.sh which drives the packaged
    s-nail binary in batch mode (version banner, command interpreter,
    addrcodec, POSIX -e semantics)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
