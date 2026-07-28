import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return

        test_dir = os.path.join(self.build_folder, "functional_test")
        os.makedirs(test_dir, exist_ok=True)
        par = os.path.join(self.dependencies["parchive"].cpp_info.bindirs[0], "par")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run('sh "{}" "{}"'.format(test_script, par), cwd=test_dir, env="conanrun")
