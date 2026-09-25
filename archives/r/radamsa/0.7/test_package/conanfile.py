import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包存在")
            return
        dep = self.dependencies["radamsa"]
        binpath = os.path.join(dep.package_folder, "bin", "radamsa")
        work = os.path.join(self.build_folder, "radwork")
        os.makedirs(work, exist_ok=True)
        # TMPDIR 指到可写构建目录（HMFS；/tmp 只读，见 notes/device-facts §一）
        self.run(f'TMPDIR="{work}" /bin/sh "{os.path.join(self.source_folder, "test.sh")}" '
                 f'"{binpath}" "{work}"', env="conanrun")
