from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["bareos-client"].package_folder
        # L0c/R34: standalone test source executed via self.run
        # (bacula-fd precedent). bareos-fd needs a live Director for real
        # backups (absent on OHOS), so the test verifies package presence,
        # executability, ELF identity plus a real --version execution.
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_bareos_fd.py")
        self.run("python3 '%s' '%s'" % (test_script, pkg), env="conanrun")
