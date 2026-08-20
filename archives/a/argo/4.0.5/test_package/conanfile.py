#!/usr/bin/env python3
"""test_package for argo executable — runs test.sh which invokes the binary."""
from conan import ConanFile


class ArgoTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) is the default shell.
        # test.sh uses #!/system/bin/sh shebang for portability.
        self.run("sh test.sh", env="conanrun")
