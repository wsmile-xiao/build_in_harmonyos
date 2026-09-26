import os

from conan import ConanFile
from conan.errors import ConanException


class PullseqTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["pullseq"].cpp_info.bindir
        script = os.path.join(os.path.dirname(__file__), "smoke.sh")
        ret = self.run(f'sh "{script}" "{bindir}"', env="conanrun", ignore_errors=True)
        if ret != 0:
            raise ConanException(f"pullseq smoke test failed rc={ret}")
