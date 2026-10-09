import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class ToposortTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Conan 2.29 needs the consumer edge to request runtime environment
        # propagation for this unknown-type, pure-Python package.
        self.requires(self.tested_reference_str, run=True)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        script = os.path.join(self.source_folder, "functional.py")
        package_dir = os.path.join(
            self.dependencies["toposort"].package_folder, "lib", "python")
        command = "python3 {} {}".format(
            shlex.quote(script), shlex.quote(package_dir))
        self.run(command, env="conanrun")
