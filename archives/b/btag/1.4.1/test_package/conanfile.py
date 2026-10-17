#!/usr/bin/env python3
"""Consumer test for the packaged btag executable."""
import os

from conan import ConanFile


class BtagTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL")
        if not bash:
            ohos_bash = "/data/service/hnp/bin/bash"
            bash = ohos_bash if os.path.exists(ohos_bash) else "/bin/bash"
        self.run(f'"{bash}" test.sh', env="conanrun")
