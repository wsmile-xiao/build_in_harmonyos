import os

from conan import ConanFile


class AsahiScriptsTestConan(ConanFile):
    """test_package for asahi-scripts — runs asahi-diagnose to verify installed scripts."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must actually execute the installed binary
        # asahi-diagnose is a self-contained shell script that produces diagnostic output
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
