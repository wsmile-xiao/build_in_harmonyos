#!/usr/bin/env python3
"""Conan test_package for Intel(R) PCM 202502 on HarmonyOS PC."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class PcmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Deliberately no can_run() guard here.  The packaged artifacts are the
        # subject of this test, so the test has to execute them and report what
        # really happens; a host/arch mismatch must show up as a failing
        # assertion, never as a silent skip.  can_run() is not even usable for
        # the destructive negative check the CI gate runs (`conan test -pr
        # <profile>` applies that profile to the host context only, leaving the
        # build context on `default`), which made the whole test() body vanish
        # and looked exactly like a hollow test.
        dep = self.dependencies["pcm"]
        pkg_folder = dep.package_folder
        if not os.path.isdir(os.path.join(pkg_folder, "bin")):
            raise ConanException("packaged pcm has no bin/ directory")
        bash = (
            os.environ.get("CONFIG_SHELL")
            or os.environ.get("SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        if not (bash and os.path.isfile(bash)):
            raise ConanException(f"no bash interpreter available for the test (got {bash!r})")
        self.run(
            f'cd "{self.source_folder}" && '
            f'PCM_PKG_FOLDER="{pkg_folder}" "{bash}" test.sh',
            env="conanrun",
        )