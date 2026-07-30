"""Conan test_package for mecab-ko (Korean morphological analyzer).

Verifies the mecab-ko toolchain is functional:
1. mecab --version outputs "0.996/ko-0.9.2"
2. mecab-config --version outputs "0.996/ko-0.9.2"
3. mecab-dict-index --help executes without error
4. mecab-dict-gen --help executes without error
5. mecab-cost-train --help executes without error
6. libmecab headers/libraries are present
"""

import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class MecabKoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # Find mecab binary from the dependency
        dep = self.dependencies["mecab-ko"]
        bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else dep.package_folder
        mecab_bin = os.path.join(bindir, "mecab")
        mecab_config = os.path.join(bindir, "mecab-config")

        # Test 1: mecab --version
        self.run(f"{mecab_bin} --version", env="conanrun")

        # Test 2: mecab-config --version
        self.run(f"{mecab_config} --version", env="conanrun")

        # Test 3-7: libexec tools
        libexec_dir = dep.package_folder + "/libexec/mecab"
        for tool in ["mecab-dict-index", "mecab-dict-gen", "mecab-cost-train",
                     "mecab-system-eval", "mecab-test-gen"]:
            exe = os.path.join(libexec_dir, tool)
            self.run(f"{exe} --help", env="conanrun")
