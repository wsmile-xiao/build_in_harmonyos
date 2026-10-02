import os
import shutil

from conan import ConanFile


class UdfclientTestConan(ConanFile):
    """test_package for udfclient — functional consumer test (R34/PF3).

    Creates a UDF image with the packaged newfs_udf, reads it back with
    udfdump (sequential descriptor scan + mount/volume-set/tree dump) and
    mounts it read-only with the interactive udfclient.  Also exercises the
    usage banner of all six tools and a missing-image negative control.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap with
        # bash (same convention as the repository executable test template).
        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
