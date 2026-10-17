import os

from conan import ConanFile


class BtopTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = "/system/bin/sh" if self.settings.os == "OHOS" else "sh"
        script = os.path.join(self.source_folder, "test_btop.sh")
        self.run("{} {}".format(shell, script), env="conanrun")

