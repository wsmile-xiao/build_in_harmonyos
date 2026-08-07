import os

from conan import ConanFile


class AggregateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # VirtualRunEnv injects deps' bindirs but not the tested package's
        # own bin/ (it is already installed in the package folder by package()).
        # Append the package bin so the test.sh `aggregate` call resolves.
        pkg_bin = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "bin")
        self.run(f"PATH=\"{pkg_bin}:$PATH\" sh test.sh", env="conanrun")
