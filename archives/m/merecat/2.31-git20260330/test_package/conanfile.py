#!/usr/bin/env python3
"""Conan consumer test for merecat 2.31-git20260330.

Uses the packaged server the way a downstream consumer would: start it on a
loopback port with a throw-away document root, fetch a file over plain HTTP and
verify the payload that comes back.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class MerecatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    # E386: probe the shells, some of them cannot resolve the working directory
    # inside the Conan cache on HMDFS.
    _SHELL_CANDIDATES = ("/bin/sh", "/usr/bin/sh", "/data/service/hnp/bin/bash")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = self._working_shell()
        work = os.path.join(self.source_folder, "merecat-consumer-test")
        self.run(f'"{shell}" test.sh "{work}"', env="conanrun")

    def _working_shell(self):
        for candidate in self._SHELL_CANDIDATES:
            if not os.path.exists(candidate):
                continue
            try:
                probe = subprocess.run([candidate, "-c", "pwd"], cwd=self.source_folder,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       universal_newlines=True, timeout=60)
            except (OSError, subprocess.SubprocessError):
                continue
            if probe.returncode == 0 and not probe.stderr.strip() and probe.stdout.strip():
                return candidate
        raise ConanException("no shell can resolve the working directory")
