import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class TpmToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        self.run("./tpm_tools_consumer", env="conanrun")
        # The shipped command line tools expose --version/--help paths that do
        # not need a TPM device, so two of them are smoke tested here too; they
        # are invoked from the package folder, the way a consumer that only
        # depends on the package would run them.  (Only tpm_version's usage
        # path exits 0 - the nv* tools print their usage and exit 255, so they
        # are not usable as an unattended smoke test.)
        bindir = os.path.join(self.dependencies["tpm-tools"].package_folder, "bin")
        self.run('"%s/tpm_version" --version' % bindir, env="conanrun")
        self.run('"%s/tpm_version" --help' % bindir, env="conanrun")
