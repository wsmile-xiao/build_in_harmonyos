import os

from conan import ConanFile


class SuperoptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["superopt"]
        bindir = str(dep.cpp_info.bindirs[0])
        if not os.path.isabs(bindir):
            bindir = os.path.join(str(dep.package_folder), bindir)
        binary = os.path.join(bindir, "superopt-sparc")
        script = os.path.join(os.path.dirname(__file__), "test_superopt.sh")
        self.run('sh "{}" "{}"'.format(script, binary))
