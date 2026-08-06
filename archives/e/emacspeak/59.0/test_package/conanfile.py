import os

from conan import ConanFile


class EmacspeakTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["emacspeak"].package_folder
        share_dir = os.path.join(pkg_folder, "share", "emacspeak")
        # R34: verify the packaged artifact — check key Lisp files exist
        # and are non-empty, verify server scripts, and check directory structure.
        self.run(f"bash test_emacspeak.sh {share_dir}", env="conanrun")
        self.output.info("emacspeak: OK")
