import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class SparseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        if self.source_folder != self.build_folder:
            copy(self, "test.c", src=self.source_folder, dst=self.build_folder)

    def test(self):
        # R34: execute the tested binary and verify it performs static analysis
        self.run("sparse --version", env="conanrun")
        # test.c contains "if (foo = 1)" — an assignment-in-condition
        # sparse should detect and warn about this pattern
        test_c = os.path.join(self.build_folder, "test.c")
        self.run(f'sparse "{test_c}"', env="conanrun")
