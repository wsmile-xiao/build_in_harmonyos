import os

from conan import ConanFile


class MbpfanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 consumer: exercise the packaged tool end-to-end via test.sh
        # (OHOS /system/bin/sh cannot exec ELF; use the hnp bash explicitly,
        # same approach as aaphoto 0.45).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh', env="conanrun")
