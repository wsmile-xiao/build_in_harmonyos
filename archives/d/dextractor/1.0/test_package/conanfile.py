import os

from conan import ConanFile


class DextractorTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the built binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，用 bash 包裹执行。
        # conanrun env 提供 PATH（bin/）与 LD_LIBRARY_PATH（hdf5 的 lib/）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
