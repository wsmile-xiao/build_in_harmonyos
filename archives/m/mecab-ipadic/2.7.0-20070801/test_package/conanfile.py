#!/usr/bin/env python3
"""test_package for mecab-ipadic 2.7.0-20070801.

Calls the standalone test script test_mecab_ipadic.py via self.run()
for CI L0d gate compliance. Tests: file existence, EUC-JP encoding,
entry counts, and optional mecab tokenization smoke test.
"""
import os

from conan import ConanFile


class MecabIpadicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["mecab-ipadic"]
        dic_dir = os.path.join(dep.package_folder, "dic")
        self.run(f"python3 test_mecab_ipadic.py \"{dic_dir}\"", cwd=self.source_folder, env="conanrun")
