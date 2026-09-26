import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # libasm.h 会 #include <gelf.h>（由 elfutils 依赖提供），
        # 头闭包自检要带上所有依赖的 include。
        incs = []
        libdirs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libdirs += _d.cpp_info.libdirs
        inc = " ".join(incs)
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-lasm", "-lelf", "-ldw"]
                        + ["-Wl,-rpath," + p for p in libdirs])
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_probe {inc} {link}")
        # 端到端消费者用例（鸿蒙特有）：libasm 产汇编 → as 汇编 → readelf/libelf 校验
        self.run(f"{cc} test_e2e.c -o test_e2e {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
        self.run(f"{bash} -c './test_e2e'", env="conanrun")
