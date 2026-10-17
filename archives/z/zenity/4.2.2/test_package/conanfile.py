#!/usr/bin/env python3
"""Consumer test for zenity 4.2.2.

R34: the test must actually exercise the packaged zenity binary.
Runs test.sh (via the configured shell), which invokes `zenity
--version` and `zenity --help` — both are handled by GOption /
handle-local-options BEFORE g_application_run starts the AdwApplication
and touches the display-less Broadway backend, so they run headless.
Full dialog rendering requires a display session (see MANIFEST.yml).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class ZenityTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: zenity binary runs on OHOS device"
            )
            return
        # R34: actually run the packaged zenity binary via test.sh
        bash = os.environ.get(
            "CONFIG_SHELL", "/data/service/hnp/bin/bash"
        )
        self.run(f"{bash} test.sh", env="conanrun")
