import os

from conan import ConanFile


class BoidsTestConan(ConanFile):
    """test_package for boids — runs the 17-case Node.js functional test suite
    against the installed module (consumed through NODE_PATH supplied by the
    recipe's runenv_info)."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS mksh may be unreliable for the runner; use bash explicitly.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")