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
        dep = self.dependencies["ondir"]
        binpath = os.path.join(dep.package_folder, "bin", "ondir")
        work = os.path.join(self.build_folder, "odwork")
        os.makedirs(work, exist_ok=True)
        # HMFS sh 的 here-doc 临时文件无视 TMPDIR 硬落只读 /tmp
        # （ctemplate CI #44049 实测）→ 改用 hnp bash + TMPDIR 重定向
        self.run(f'TMPDIR="{work}" /data/service/hnp/bin/bash "{os.path.join(self.source_folder, "test.sh")}" '
                 f'"{binpath}" "{work}"', env="conanrun")
