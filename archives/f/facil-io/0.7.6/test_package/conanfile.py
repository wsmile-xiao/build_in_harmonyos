import os

from conan import ConanFile


class FacilIoTestConan(ConanFile):
    """test_package for facil.io — compiles and runs an in-process HTTP
    server/client consumer program linked against the installed lib (R34)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies[self.tested_reference_str]
        incdirs = ";".join(os.path.join(dep.package_folder, d) for d in dep.cpp_info.includedirs)
        lib = os.path.join(dep.package_folder, "lib")
        self.run(f'FIO_INCS="{incdirs}" FIO_LIB="{lib}" {bash} test.sh', env="conanrun")
