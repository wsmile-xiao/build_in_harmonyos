#!/usr/bin/env python3
"""test_package for mecab-unidic 2.1.2.

Calls the standalone test script test_mecab_unidic.py via self.run()
for CI L0d gate compliance. Tests: file existence, lex.csv entry count,
matrix.def size, UTF-8 encoding, dicrc sanity, binary indices (required),
OHOS package layout, and real mecab consumption (links libmecab.a from the
required mecab/0.996 package and loads this dictionary) — fail-closed.
"""
import os

from conan import ConanFile


class MecabUnidicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Real consumer dependency: link mecab/0.996 libmecab.a and load this
        # dictionary in the consumption test.
        self.requires("mecab/0.996")

    def test(self):
        dep = self.dependencies["mecab-unidic"]
        mecab = self.dependencies["mecab"]
        dic_dir = os.path.join(dep.package_folder, "dic")
        self.run(f'python3 test_mecab_unidic.py "{dic_dir}" "{mecab.package_folder}"',
                 cwd=self.source_folder, env="conanrun")
