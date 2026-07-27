import os

from conan import ConanFile


class PerlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        perl = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
        assert os.path.isfile(perl), f"Perl executable not found at {perl}"
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        program = "use strict; use warnings; use File::Spec; print qq(perl-ok\\n);"
        self.run(f'"{shell}" -c "\"{perl}\" -e \'{program}\'"', env="conanrun")
