#!/usr/bin/env python3
"""Consumer test package for adms — 真实调用 admsXml/admsCheck 二进制."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AdmsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["adms"].cpp_info.bindirs[0]
        adms_xml = os.path.join(bindir, "admsXml")
        adms_check = os.path.join(bindir, "admsCheck")
        if not os.path.isfile(adms_xml):
            raise ConanException(f"missing packaged executable: {adms_xml}")
        if not os.path.isfile(adms_check):
            raise ConanException(f"missing packaged executable: {adms_check}")
        if not can_run(self):
            self.output.info("cross build: binaries exist; runtime verified on the OHOS device")
            return
        script = os.path.join(self.source_folder, "test_adms.py")
        self.run(f'"{sys.executable}" "{script}" "{adms_xml}" "{adms_check}"', env="conanrun")
