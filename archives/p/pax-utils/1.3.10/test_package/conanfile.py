import os

from conan import ConanFile


class PaxUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pax-utils"]
        pkg = str(dep.package_folder)
        bindir = str(dep.cpp_info.bindirs[0])
        if not os.path.isabs(bindir):
            bindir = os.path.join(pkg, bindir)
        script = os.path.join(os.path.dirname(__file__), "test_pax_utils.sh")
        self.run('sh "{}" "{}" "{}"'.format(script, bindir, pkg))
