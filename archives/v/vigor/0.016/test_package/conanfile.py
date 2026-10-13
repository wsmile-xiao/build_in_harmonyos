import os

from conan import ConanFile


class VigorTestConan(ConanFile):
    """test_package for the vigor executable.

    Runs vigor_test.py under the conanrun environment (PATH + LD_LIBRARY_PATH
    populated from the package and its tcl/tk/X11 chain).  The script really
    executes the installed `vigor` binary and performs HarmonyOS-specific
    assertions (aarch64 ELF, dynamic-link resolution).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34/PF3: test() must actually execute the packaged binary.
        # OHOS: /system/bin/sh (mksh) cannot exec ELF directly — run the
        # checks from python under the conanrun environment instead.
        self.run("python3 vigor_test.py", env="conanrun")
