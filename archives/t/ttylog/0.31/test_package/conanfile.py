"""Execute the delivered ttylog binary, not an unrelated smoke program."""

import os
import shutil
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class TtylogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_ttylog.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        binary = os.path.join(self.dependencies["ttylog"].package_folder, "bin", "ttylog")
        runner = ""
        if self.settings.os == "OHOS":
            runner = shutil.which("qemu-aarch64") or ""
            if not runner:
                self.output.warning("SKIP: qemu-aarch64 unavailable on x86 runner; no runtime tests claimed")
                return
        script = os.path.join(self.source_folder, "test_ttylog.py")
        self.run(f'"{sys.executable}" "{script}" "{binary}" "{runner}"', env="conanrun")
