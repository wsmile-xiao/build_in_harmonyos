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
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = os.environ.get("CC", executables.get("c", "cc"))
        self.run(f'{cc} test_consumer.c -o test_consumer')

    def test(self):
        bin_dir = os.path.join(self.dependencies["awesfx"].package_folder, "bin")
        paths = [os.path.join(bin_dir, tool) for tool in ("sf2text", "text2sf")]
        self.run("./test_consumer " + " ".join(f'\"{path}\"' for path in paths))
        for tool in ("sf2text", "text2sf"):
            path = os.path.join(bin_dir, tool)
            result = subprocess.run([path, "--help"], capture_output=True, text=True)
            output = (result.stdout or "") + (result.stderr or "")
            assert "usage" in output, f"{tool} did not print usage"
