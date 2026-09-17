import os

from conan import ConanFile


class PexecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pexec"]
        bindir = str(dep.cpp_info.bindirs[0])
        if not os.path.isabs(bindir):
            bindir = os.path.join(str(dep.package_folder), bindir)
        pexec = os.path.join(bindir, "pexec")
        script = os.path.join(os.path.dirname(__file__), "test_pexec.sh")
        self.run('sh "{}" "{}"'.format(script, pexec))
