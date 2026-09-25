import os

from conan import ConanFile


class WrenCliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["wren-cli"]
        bindir = str(dep.cpp_info.bindirs[0])
        if not os.path.isabs(bindir):
            bindir = os.path.join(str(dep.package_folder), bindir)
        exe = os.path.join(bindir, "wren_cli")
        script = os.path.join(os.path.dirname(__file__), "test_wren_cli.sh")
        self.run('sh "{}" "{}"'.format(script, exe))
