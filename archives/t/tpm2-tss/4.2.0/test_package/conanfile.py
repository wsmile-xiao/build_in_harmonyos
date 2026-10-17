import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 收集全部依赖的 include（tss2 头会拉 openssl 等）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        cc = os.environ.get("CC", "clang")
        self.run(f'{cc} test_tss.c -o test_probe {" ".join(incs)} -ldl')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：仅验证编译通过（探针在目标机上运行）")
            return
        libdir = os.path.join(self.dependencies["tpm2-tss"].package_folder, "lib")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 探针自身 dlopen 各库，故需 lib 目录可被动态加载器找到。
        self.run(f'{bash} -c "./test_probe {libdir}"',
                 env="conanrun")
