from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            tool = os.path.join(self.dependencies["cc-tool"].package_folder,
                                "bin", "cc-tool")
            if not os.path.isfile(tool):
                raise RuntimeError("cc-tool executable missing from package")
            self.run("sh {} {}".format(
                os.path.join(self.source_folder, "test.sh"), tool), env="conanrun")
