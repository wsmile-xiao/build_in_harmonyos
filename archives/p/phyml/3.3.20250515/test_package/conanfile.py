"""Run a small nucleotide alignment through the packaged PhyML CLI."""

import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class PhymlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "alignment.phy", "test_phyml.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            raise RuntimeError("PhyML consumer could not run on this platform")
        binary = Path(self.dependencies["phyml"].package_folder) / "bin" / "phyml"
        alignment = Path(self.build_folder) / "alignment.phy"
        shutil.copyfile(Path(self.source_folder) / "alignment.phy", alignment)
        script = Path(self.source_folder) / "test_phyml.sh"
        self.run(f'sh "{script}" "{binary}" "{alignment}"',
                 cwd=self.build_folder, env="conanrun")
