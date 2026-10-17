import os

from conan import ConanFile


class ScanelfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["scanelf"]
        pkg = str(dep.package_folder)
        bindir = str(dep.cpp_info.bindirs[0])
        if not os.path.isabs(bindir):
            bindir = os.path.join(pkg, bindir)
        script = os.path.join(os.path.dirname(__file__), "test_scanelf.sh")
        self.run('sh "{}" "{}" "{}"'.format(script, bindir, pkg))
