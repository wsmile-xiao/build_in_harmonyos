import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class LsixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Real consumer scenario: lsix is executed by a Conan-provided bash
        # and pipes into Conan-provided ImageMagick 7 tools.
        self.requires("bash/5.3")
        self.requires("imagemagick-full/7.1.2-23")

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            lsix = os.path.join(
                self.dependencies["lsix"].package_folder, "res", "lsix"
            )
            bash = os.path.join(
                self.dependencies["bash"].package_folder, "bin", "bash"
            )
            magick = os.path.join(
                self.dependencies["imagemagick-full"].package_folder, "bin", "magick"
            )
            script = os.path.join(self.source_folder, "test.sh")
            # The test runs lsix WITHOUT a controlling tty (CI has none), so
            # the forced-SIXEL path (LSIX_FORCE_SIXEL_SUPPORT=1) is the
            # core GUI-independent behavior under test. See test.sh header.
            self.run(
                f'"{bash}" "{script}" "{lsix}" "{bash}" "{magick}"',
                env="conanrun",
            )
