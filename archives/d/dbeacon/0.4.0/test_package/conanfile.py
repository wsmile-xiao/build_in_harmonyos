#!/usr/bin/env python3
"""Consumer test for the packaged dbeacon executable."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class DbeaconTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def test(self):
        if str(self.settings.os) == "OHOS":
            # OHOS /system/bin/sh cannot execute ELF binaries; wrap with bash.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"{shlex.quote(bash)} {shlex.quote(script)}", env="conanrun")
