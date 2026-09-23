#!/usr/bin/env python3
"""test_package for nq — functional test of the packaged queue tools (R34).

The test really drives the installed binaries (not a print-only stub):

    test_nq.sh  enqueues a real background job with `nq` (sh -c echo marker),
                waits for it with `nq -w`, then asserts the marker and the
                `[exited with status 0.]` line appear in the job's log file
                (proves the job actually ran under flock ordering).  It also
                exercises `nqtail` against the completed job and verifies the
                `nqterm` wrapper is installed and executable.
"""
import os

from conan import ConanFile


class NqTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the functional suite with bash (CONFIG_SHELL) and the packaged
        # bin/ dir on PATH (via conanrun env from runenv_info).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{0} test_nq.sh".format(bash), env="conanrun")
