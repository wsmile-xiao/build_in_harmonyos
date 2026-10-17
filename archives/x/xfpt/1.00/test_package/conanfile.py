#!/usr/bin/env python3
"""Conan test_package for xfpt 1.00.

Verifies that the installed xfpt binary and its share data files are
usable by a consumer: version output, usage, error path, and a real
marked-up text -> DocBook XML conversion using the packaged share
directory (stdflags/stdmacs) via -S.
"""
import os
import shutil

from conan import ConanFile


class XfptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg = self.dependencies["xfpt"].package_folder
        xfpt_bin = os.path.join(pkg, "bin", "xfpt")
        share_dir = os.path.join(pkg, "share", "xfpt")

        assert os.path.isfile(xfpt_bin), f"xfpt binary not found at {xfpt_bin}"
        assert os.path.isdir(share_dir), f"xfpt share dir not found at {share_dir}"

        # Find bash: prefer CONFIG_SHELL, then PATH lookup, then OHOS default
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(
            f'XFPT_BIN="{xfpt_bin}" XFPT_SHARE="{share_dir}" {bash} test_xfpt.sh',
            env="conanrun",
        )
