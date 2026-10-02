import os
import sys

from conan import ConanFile


class LibscrcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = str(self.dependencies["libscrc"].package_folder)
        test_script = os.path.join(self.source_folder, "test_consumer.py")
        self.run('"{}" "{}" "{}"'.format(sys.executable, test_script, package_folder),
                 env="conanrun")
