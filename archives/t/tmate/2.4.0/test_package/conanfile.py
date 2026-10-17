#!/usr/bin/env python3
"""test_package for tmate 2.4.0 — runs the real test_tmate.sh smoke test.

The test source (test_tmate.sh) actually executes the packaged `tmate -V` and
strictly asserts the output equals `tmate 2.4.0` (L0c: real test source, no
fake/echo/empty tests). Runs with env="conanrun" so dependency shared
libraries (libevent.so from ohpcd) are resolvable at runtime via the generated
LD_LIBRARY_PATH.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TmateTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(bindir, "bin", "tmate")
        if not os.path.isfile(binary):
            raise RuntimeError(f"tmate binary missing: {binary}")

        if can_run(self):
            # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
            # Use bash to wrap binary execution, mirroring the executable
            # test_package template.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'TMATE_BIN="{binary}" {bash} test_tmate.sh', env="conanrun")
        else:
            self.output.info("TMATE_SKIP_RUN (cross target cannot run locally)")
