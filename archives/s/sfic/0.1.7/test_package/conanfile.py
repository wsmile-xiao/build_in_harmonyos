import os

from conan import ConanFile


class SficTestConan(ConanFile):
    """Consumer test: drive the installed sfic CLI as an end user would —
    build a tdb metadata database of a file tree, list it, rebuild it and
    compare databases to verify change detection."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries — wrap in bash.
        # conanrun env: PATH points at sfic's bin/, LD_LIBRARY_PATH covers
        # libtdb.so.1 from the tdb dependency package.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
