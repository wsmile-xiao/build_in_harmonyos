#!/usr/bin/env python3
"""test_package for exifprobe executable — runs test.sh which invokes the
installed `exifprobe` binary on a real EXIF-carrying JPEG and verifies
observable parse output (consumer validation on the OHOS target)."""
import os

from conan import ConanFile


class ExifprobeTestConan(ConanFile):
    """test_package for exifprobe executable."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
