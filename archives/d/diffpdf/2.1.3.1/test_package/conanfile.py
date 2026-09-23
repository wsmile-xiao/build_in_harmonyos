import os

from conan import ConanFile


class DiffpdfTestConan(ConanFile):
    """test_package for the diffpdf executable (Qt5 GUI application).

    R40: diffpdf is a Qt GUI app. OHOS PC has no guaranteed graphical
    Qt platform plugin runtime, so verification is link-level +
    CLI-level: `diffpdf --help` exercises QApplication construction,
    argument parsing and the usage output path (main.cpp returns 0
    right after printing usage). The offscreen platform plugin shipped
    by qt5-qtbase is used to avoid requiring a display.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (acetoneiso recipe pattern).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
