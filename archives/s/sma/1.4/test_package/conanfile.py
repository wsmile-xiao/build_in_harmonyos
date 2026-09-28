import os

from conan import ConanFile


class SmaTestConan(ConanFile):
    """test_package for the sma executable.

    sma is a text-in / report-out analyser, so the consumer test feeds a small
    synthetic sendmail log and asserts on the report text it prints back
    (falsifiable: change the log and the numbers change).  No display, no
    device node and no network involved.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries -> bash wrapper.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")

