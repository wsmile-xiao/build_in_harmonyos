import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（同仓 dieharder 手法）：#include 公共头
        # <kernelshark/libkshark.h> 并 -lkshark —— L1e 把包 include/、lib/
        # 移走再跑一次时，两处都必须真实依赖才会失败
        incs, linkdirs = [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            linkdirs += [p for p in _d.cpp_info.libdirs if os.path.isdir(p)]
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        link = " ".join(["-L" + p for p in linkdirs]
                        + ["-Wl,-rpath-link," + p for p in linkdirs])
        self.run("{cc} test_kernelshark.c -o test_probe {inc} {link} -lkshark".format(
            cc=cc, inc=" ".join(incs), link=link))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 设备 HNP bash getcwd() 怪癖：按名进入后恢复正常；用 python 侧的
        # 绝对 cwd 传给 cd（同仓 dieharder 手法）
        cwd = os.getcwd()
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 运行时闭包（vendored trace 三库 + json-c）由 conanrun 的
        # LD_LIBRARY_PATH 提供；libz 来自系统 /system/lib64/ndk
        self.run("{bash} -c 'cd {cwd} && ./test_probe'".format(bash=bash, cwd=cwd),
                 env="conanrun")
