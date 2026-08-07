#!/usr/bin/env python3
"""test_package for mecab-ko-dic 2.1.1-20180720.

Calls the standalone test script test_mecab_ko_dic.py via self.run()
for CI L0d gate compliance. Tests: file existence, UTF-8 encoding,
entry counts, and optional mecab tokenization smoke test.
"""
import os

from conan import ConanFile


class MecabKoDicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["mecab-ko-dic"]
        dic_dir = os.path.join(dep.package_folder, "dic")
        self.run(f"python3 test_mecab_ko_dic.py \"{dic_dir}\"", cwd=self.source_folder, env="conanrun")
