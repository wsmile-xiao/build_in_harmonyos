#!/usr/bin/env python3
"""Conan test_package — osmid 0.8.0-repack (CLI smoke test).

osmid is a command-line tool (no linkable library): the consumer test really
executes the packaged `m2o`/`o2m` binaries. --help exits 1 with the cxxopts
help text before any MIDI/ALSA access, so headless environments can validate
executability and output; --version is NOT used because it continues into the
MIDI open + heartbeat loop and would hang. The negative case pins a non-zero
exit for an unknown option, so a stub binary or empty-output fake cannot pass.
"""

import os

from conan import ConanFile


class OsmidTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot reliably execute ELF binaries.
        # Use bash to wrap binary execution (cldump/xsel precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} test_osmid.sh".format(bash), env="conanrun")
