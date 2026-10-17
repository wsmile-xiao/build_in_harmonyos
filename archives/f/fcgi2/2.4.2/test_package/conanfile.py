import os

from conan import ConanFile


class Fcgi2TestConan(ConanFile):
    """test_package for fcgi2 — compiles and runs a CGI-mode consumer program
    linked against the installed libfcgi (R34)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies[self.tested_reference_str]
        inc = os.path.join(dep.package_folder, "include")
        lib = os.path.join(dep.package_folder, "lib")
        self.run(f'FCGI_INC="{inc}" FCGI_LIB="{lib}" {bash} test.sh', env="conanrun")
