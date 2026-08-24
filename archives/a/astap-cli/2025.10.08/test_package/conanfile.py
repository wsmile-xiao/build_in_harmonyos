#!/usr/bin/env python3
from conan import ConanFile


class AstapCliTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run(f"TEST_SOURCE_DIR=\"{self.source_folder}\" /data/service/hnp/bin/bash {self.source_folder}/test_astap_cli.sh", env="conanrun")
