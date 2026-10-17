import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.tools.files import load, save


class ScdocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if str(self.settings.os) == "OHOS":
            return
        save(self, "input.scd", "scdoc(1)\n===============\n\n# NAME\n\nscdoc test.\n")
        self.run("scdoc < input.scd > output.1", env="conanrun")
        output = load(self, "output.1")
        if ".TH" not in output or "scdoc" not in output:
            raise RuntimeError("scdoc did not generate a roff page")
