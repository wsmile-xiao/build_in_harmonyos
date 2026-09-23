#!/usr/bin/env python3
import os

from conan import ConanFile


class LibzpaqTestConan(ConanFile):
    """test_package for libzpaq — CLI archiver roundtrip test."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries
        # reliably; wrap with bash (aa3d/aamath precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Expose the packaged share/libzpaq config dir to the test script
        dep = self.dependencies["libzpaq"]
        cfg_dir = os.path.join(dep.package_folder, "share", "libzpaq")
        self.run(
            f'CONAN_LIBZPAQ_CFG_DIR="{cfg_dir}" {bash} test.sh',
            env="conanrun",
        )
