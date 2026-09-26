import os

from conan import ConanFile


class MultirunTestConan(ConanFile):
    """test_package for the multirun executable — runs test.sh which exercises
    the installed binary with real concurrent-command scenarios
    (mirrors upstream tests.bats)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # multirun spawns `sh -c` children and forwards signals to process
        # groups; wrap with bash for reliable execution on OHOS.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")