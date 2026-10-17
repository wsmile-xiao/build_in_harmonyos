from conan import ConanFile
from conan.tools.build import can_run
import os

class GnuPGTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    requires = "gnupg/2.4.9.1"

    def test(self):
        if not can_run(self):
            return
        self.run("/data/service/hnp/bin/bash test_gnupg.sh", env="conanrun", cwd=self.source_folder)
