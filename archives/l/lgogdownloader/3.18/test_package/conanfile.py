import os
import tempfile

from conan import ConanFile


class LgogdownloaderTestConan(ConanFile):
    """test_package — consumer test for the lgogdownloader command line tool.

    Delegates the real verification to two shell scripts:
      * test_lgogdownloader.sh — upstream-equivalent smoke checks (version/help)
      * ohos_specific_test.sh  — HarmonyOS-specific platform checks
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        binary = os.path.join(
            self.dependencies["lgogdownloader"].package_folder,
            "bin",
            "lgogdownloader",
        )
        # Keep every generated artifact out of the recipe folder.
        base = os.environ.get("TMPDIR") or os.environ.get("HOME") or "/tmp"
        work = tempfile.mkdtemp(prefix="lgogdownloader-test-", dir=base)
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap the
        # invocations in bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        smoke = os.path.join(self.source_folder, "test_lgogdownloader.sh")
        ohos = os.path.join(self.source_folder, "ohos_specific_test.sh")
        self.run(f'{bash} "{smoke}" "{binary}" "{work}"', env="conanrun")
        self.run(f'{bash} "{ohos}" "{binary}" "{work}"', env="conanrun")
