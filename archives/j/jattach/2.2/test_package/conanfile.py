#!/usr/bin/env python3
"""Conan test_package for jattach 2.2.

test_jattach.sh drives the installed `jattach` binary (R34 — no print-only
stub): CLI contract (usage/exit codes, PID validation), /proc-based process
lookup, and the real HotSpot attach trigger path (.attach_pid file creation
+ SIGQUIT delivery) against a live dummy process.  See the script for the
full assertion list.
"""

import os

from conan import ConanFile


class JattachTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run("{0} test_jattach.sh".format(bash), env="conanrun")
