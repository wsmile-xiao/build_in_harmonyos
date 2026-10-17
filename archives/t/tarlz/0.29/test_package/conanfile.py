#!/usr/bin/env python3
"""Consumer test for tarlz/0.29 (tool package).

Runs the installed `tarlz` binary through a shell roundtrip
(version, create .tar.lz, list, extract + byte-compare).
"""
from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.layout import basic_layout


class TarlzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at
        # a /usr/local/lib whose incompatible libxml2.so.16 breaks the
        # SDK's lld on every link — CI-021 build #48068, libabw precedent).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            self.run("sh test_tarlz.sh tarlz", cwd=self.source_folder,
                     env="conanrun")
