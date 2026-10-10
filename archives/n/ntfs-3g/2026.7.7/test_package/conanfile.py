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
        # mkntfs/ntfsinfo/ntfsls 链接包内 lib/libntfs-3g.so.90,包 lib/ 不在
        # loader 默认搜索路径 → 报 "Error loading shared library
        # libntfs-3g.so.90" + 一屏 "symbol not found"。
        # OHOS 上 conan 的 env 列表不生效,须在命令内联 LD_LIBRARY_PATH
        # (acsccid/1.1.13 等 2800+ 配方同款做法)。
        pkg_libdir = dep.cpp_info.libdirs[0]
        script = os.path.join(self.source_folder, "test_ntfs3g_cli.sh")
        self.run(f"LD_LIBRARY_PATH={pkg_libdir} /bin/sh {script} "
                 f"{pkg_bindir} {self.source_folder}")
