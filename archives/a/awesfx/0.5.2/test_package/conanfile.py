from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain
import os
import subprocess


class AwesfxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        self.run("true")

    def test(self):
        bin_dir = os.path.join(self.dependencies["awesfx"].package_folder, "bin")
        for tool in ("sf2text", "text2sf"):
            path = os.path.join(bin_dir, tool)
            result = subprocess.run([path], capture_output=True, text=True)
            output = (result.stdout or "") + (result.stderr or "")
            assert "usage" in output, f"{tool} did not print usage"
