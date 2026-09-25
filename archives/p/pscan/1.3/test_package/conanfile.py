import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        pkg_bindir = dep.cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_pscan_cli.sh")
        # 上游 test.c 随包交付在 bin/ 下(conanfile package() 特意拷贝),供扫描断言
        self.run(f"/bin/sh {script} {os.path.join(pkg_bindir, 'pscan')} {pkg_bindir}")
