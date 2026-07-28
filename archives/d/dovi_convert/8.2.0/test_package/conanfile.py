#!/usr/bin/env python3
"""Conan test_package for dovi_convert 8.2.0.

Verifies the dovi_convert CLI is installed and executable, and that
its help/usage path works without invoking external media tools
(ffmpeg/mkvmerge/dovi_tool/mediainfo) — those are runtime deps the
user installs separately and are not available in the Conan test env.
"""
import os
import shutil

from conan import ConanFile


class DoviConvertTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: use bash wrapper (mksh cannot exec some ELFs cleanly)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_dovi_convert.sh")
        self.run(f'{bash} "{script}"', env="conanrun")
