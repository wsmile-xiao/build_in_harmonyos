#!/usr/bin/env python3
"""Conan test_package for lftp 4.9.3.

lftp is a command-line file transfer client (no linkable library), so the
consumer test executes the packaged binary: a --version smoke check plus
test_lftp.sh, which runs four offline functional checks (version string,
help output, queued kill/jobs behaviour ported from upstream
tests/lftp-queue-kill, local lcd/lpwd) and prints HMBS_TEST_PACKAGE_RESULT
itself -- the marker flows through self.run() into the conan log with
counters owned by the script (no stdout scraping).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LftpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # VirtualRunEnv adds lftp's bin/ to PATH, so call it by name.
            self.run("lftp --version", env="conanrun")
            # OHOS has no /bin/sh guarantee: drive the script with the same
            # bash the profile provides (bash/5.3 test_package precedent).
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            script = os.path.join(self.source_folder, "test_lftp.sh")
            self.run('"%s" "%s"' % (bash, script), env="conanrun")
