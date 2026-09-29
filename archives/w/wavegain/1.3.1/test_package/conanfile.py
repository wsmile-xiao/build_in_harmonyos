#!/usr/bin/env python3
"""Consumer test for wavegain/1.3.1 (tool package).

Runs the installed `wavegain` binary: usage, gain-apply roundtrip on a
synthetic WAV, gain calculation report.
"""
from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.layout import basic_layout


class WavegainTestConan(ConanFile):
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
            self.run("sh test_wavegain.sh wavegain", cwd=self.source_folder,
                     env="conanrun")
