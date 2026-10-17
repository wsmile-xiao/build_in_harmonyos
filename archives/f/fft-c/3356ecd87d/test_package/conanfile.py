# test_package — fft-c 3356ecd87d 消费者验证
# 通过 conan 安装产物（公开头 fft.h + 库 libfft_c）编译链接并实际运行数值断言。
import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv 提供 conanrun 环境（LD_LIBRARY_PATH）；漏掉会导致
    # 编译链接全过、运行时报 `Error loading shared library`（共享库模式）。
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["fft-c"]
        inc = " ".join("-I" + p for p in dep.cpp_info.includedirs)
        libdirs = [p for _, d in self.dependencies.items() for p in d.cpp_info.libdirs]
        link = " ".join(
            ["-L" + p for p in libdirs]
            + ["-l" + l for l in dep.cpp_info.libs]
            + ["-Wl,-rpath," + p for p in libdirs]
            + ["-lm"]
        )
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} -O2 test.c -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        libdirs = []
        for _r, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_probe'",
            env="conanrun",
        )