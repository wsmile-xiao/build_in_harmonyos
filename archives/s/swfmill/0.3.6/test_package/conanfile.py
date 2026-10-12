#!/usr/bin/env python3
"""Conan test_package — swfmill 0.3.6 (application type).

Consumer verification for the swfmill CLI: invokes the installed binary via
test.sh (xml2swf + swf2xml round-trip, plus a HarmonyOS-specific
non-assertive observation per rule12).

The test logic lives in test_package/test.sh (a test source file, required
by CI L0c) so that the local W3 run and the CI run exercise exactly the
same code path.
"""
import os

from conan import ConanFile


class SwfmillTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = self.dependencies["swfmill"].cpp_info.bindirs[0]
        swfmill = os.path.join(bin_dir, "swfmill")
        share_dir = os.path.join(
            self.dependencies["swfmill"].package_folder, "share", "swfmill"
        )
        script = os.path.join(self.source_folder, "test.sh")
        # OHOS: /system/bin/sh (mksh) does not execute ELF binaries reliably.
        # Wrap with bash (same approach as the 2048.c / aa3d test_packages).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'{bash} "{script}" "{swfmill}" "{share_dir}" '
            f'"{self.build_folder}" "{self.settings.os}"',
            env="conanrun",
        )
