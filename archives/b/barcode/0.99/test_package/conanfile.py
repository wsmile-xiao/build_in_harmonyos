import os

from conan import ConanFile
from conan.tools.build import cross_building


class BarcodeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return
        barcode = os.path.join(self.dependencies["barcode"].package_folder, "bin", "barcode")
        script = os.path.join(self.recipe_folder, "test_barcode.sh")
        self.run(f'sh "{script}" "{barcode}"', env="conanrun")
