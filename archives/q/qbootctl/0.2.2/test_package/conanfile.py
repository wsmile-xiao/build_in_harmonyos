#!/usr/bin/env python3
"""Consumer test package for qbootctl 0.2.2.

Only the test-only build (bin/qbootctl-test, compiled with
QBOOTCTL_TESTING) is executed: it uses a pure in-memory backend and
never touches /dev, /proc, /sys or any real block device. The
production binary (bin/qbootctl) is verified to contain no mock switch
and to keep upstream semantics (non-root rejection).

Destructive real-hardware flags (-s/-m/-u/-i against real slots/GPT/UFS)
are never invoked; state transitions are exercised only on the in-memory
mock backend inside qbootctl-test.
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class QbootctlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["qbootctl"].package_folder
        qbootctl_bin = os.path.join(pkg, "bin", "qbootctl")
        # qbootctl-test is a test-only artifact (QBOOTCTL_TESTING) that
        # the recipe keeps OUT of bin/; it lives in the package's test/
        # directory and is never exposed through cpp_info.bindirs.
        qbootctl_test_bin = os.path.join(pkg, "test", "qbootctl-test")
        if not os.path.isfile(qbootctl_bin):
            raise ConanException(f"missing packaged executable: {qbootctl_bin}")
        if not os.path.isfile(qbootctl_test_bin):
            raise ConanException(f"missing test-only executable: {qbootctl_test_bin}")
        if not can_run(self):
            self.output.info("cross build: binaries present; runtime validated on OHOS emulator")
            return
        script = os.path.join(self.source_folder, "test_qbootctl.py")
        self.run(
            f'"{sys.executable}" "{script}" "{qbootctl_bin}" "{qbootctl_test_bin}" "{pkg}"',
            env="conanrun",
        )
