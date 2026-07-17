import os

from conan import ConanFile


class BmonTestConan(ConanFile):
    """test_package for the bmon executable — runs the installed binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} {os.path.join(self.source_folder, 'test.sh')}", env="conanrun")
