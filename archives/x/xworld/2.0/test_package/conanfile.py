#!/usr/bin/env python3
"""test_package for xworld 2.0 — smoke test runner + OHOS consumer case."""
import os

from conan import ConanFile


class XworldTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # test_package source is in test_package/ subfolder
        self.folders.generators = os.path.join(self.generators_folder_root, self.name) if hasattr(self, 'generators_folder_root') else "generators"

    def build(self):
        """Compile the OHOS consumer case (consumer.c)."""
        tp_dir = os.path.dirname(os.path.abspath(__file__))
        consumer_c = os.path.join(tp_dir, "consumer.c")
        consumer_bin = os.path.join(tp_dir, "consumer")
        if os.path.isfile(consumer_c):
            comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
            cc = comp.get("c", "cc") if comp else "cc"
            self.run(f"{cc} -Wall -O2 -o {consumer_bin} {consumer_c}", env="conanbuild")

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test.sh lives next to this conanfile.py in test_package/
        test_sh = os.path.join(os.path.dirname(__file__), "test.sh")
        self.run(f"{bash} {test_sh}", env="conanrun")
