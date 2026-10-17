import os

from conan import ConanFile


class WmtopTestConan(ConanFile):
    """Consumer test for the wmtop executable package.

    ``test.sh`` drives the installed binary through its display-independent
    code paths.  It is executed through bash because the OHOS ``/system/bin/sh``
    (mksh) cannot execute ELF binaries.
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "bash"
        self.run(f'"{bash}" test.sh', env="conanrun")
