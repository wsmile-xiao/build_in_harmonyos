import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class TagutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["tagutil"].package_folder
        binary = os.path.join(package_folder, "bin", "tagutil")
        if not os.path.isfile(binary):
            raise RuntimeError("tagutil binary missing from package")
        script = os.path.join(self.source_folder, "test_tagutil.py")
        is_ohos = str(self.settings.os) == "OHOS"
        command = '"%s" "%s" "%s" "%s" "%s"' % (
            sys.executable, script, binary, package_folder, self.build_folder)
        if is_ohos:
            command += " OHOS"
        self.run(command, env="conanrun")
