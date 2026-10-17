import os
import sys

from conan import ConanFile


class TinyarrayTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.source_folder, "test_tinyarray.py")
        self.run('"{}" "{}"'.format(sys.executable, test_script), env="conanrun")
