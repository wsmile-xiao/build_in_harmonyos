#!/usr/bin/env python3
"""Functional consumer test for abnfgen."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class AbnfgenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The OHOS profile represents the AtomCode real-device test runtime.
        # Keep the test executable when L1e invokes conan test with only its
        # host profile; the build context can otherwise default to Linux.
        if str(self.settings.os) == "OHOS" or can_run(self):
            default_shell = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL", default_shell)
            script = os.path.join(self.source_folder, "test_abnfgen.sh")
            # R34: pass the packaged abnfgen by absolute path so the
            # test genuinely depends on the package binary (moving bin/
            # away during the destructive negative test breaks this).
            pkg_folder = self.dependencies["abnfgen"].package_folder
            bin_path = os.path.join(pkg_folder, "bin", "abnfgen")
            self.run(f'{shell} "{script}" "{bin_path}"', env="conanrun")
