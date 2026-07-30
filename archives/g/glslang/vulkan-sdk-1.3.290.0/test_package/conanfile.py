import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class GlslangTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            binary = os.path.join(self.dependencies["glslang"].package_folder, "bin", "glslang")
            script = os.path.join(self.source_folder, "test.sh")
            shader = os.path.join(self.source_folder, "test.vert")
            output = os.path.join(self.build_folder, "test.spv")
            bash = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            self.run(
                f'"{bash}" "{script}" "{binary}" "{shader}" "{output}"',
                env="conanrun",
            )
