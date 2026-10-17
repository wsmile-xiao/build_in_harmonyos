#!/usr/bin/env python3
"""Conan test_package for protomol 2.0.3 — OHOS consumer test.

ProtoMol installs six command-line programs and no libraries, so the consumer
test drives the installed executables through the conanrun environment rather
than compiling against the package.

The real work happens in test.sh, which:
  * smoke-tests all six installed programs,
  * runs the upstream ``examples/argon_400`` molecular dynamics case end to end
    on the device and checks the reported step count, the energy table shape
    and the numerical result against a recorded reference.

OHOS note: /system/bin/sh (mksh) cannot exec the installed ELF binaries, so the
script is always launched through a real bash.
"""

import os

from conan import ConanFile


class ProtomolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test.sh")
        # test.sh lives next to this recipe; pass the absolute path so the
        # script can locate its own data/ directory no matter what the
        # working directory of the test build folder happens to be.
        self.run(f'{bash} "{script}"', env="conanrun")
