import os

from conan import ConanFile


class OsmiumToolTestConan(ConanFile):
    """test_package for the `osmium` executable package."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot reliably execute ELF binaries in
        # every context; use the configured bash to drive test.sh.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
