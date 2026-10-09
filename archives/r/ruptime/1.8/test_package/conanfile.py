from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout
import os


class RuptimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            # R34: run the packaged scripts for real (version banner with a
            # staged config, daemon protocol probe, syntax + shebang checks).
            bash = os.path.join(
                self.dependencies["bash"].package_folder, "bin", "bash")
            bin_dir = os.path.join(
                self.dependencies["ruptime"].package_folder, "bin")
            script = os.path.join(self.source_folder, "test_ruptime.sh")
            self.run('"%s" "%s" "%s"' % (bash, script, bin_dir),
                     env="conanrun")
            self.output.info("ruptime: OK")
