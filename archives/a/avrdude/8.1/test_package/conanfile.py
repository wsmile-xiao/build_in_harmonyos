import os
from glob import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AvrdudeTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package_folder = self.dependencies["avrdude"].package_folder
            binary = os.path.join(package_folder, "bin", "avrdude")
            configs = glob(
                os.path.join(package_folder, "**", "avrdude.conf"),
                recursive=True,
            )
            if not configs:
                raise ConanException("Packaged avrdude.conf was not found")
            script = os.path.join(self.source_folder, "test.sh")
            self.run(
                f'sh "{script}" "{binary}" "{configs[0]}"',
                env="conanrun",
            )
