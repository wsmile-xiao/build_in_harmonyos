import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libmspack"]
        incs = ["-I" + p for p in dep.cpp_info.includedirs]
        libdirs = list(dep.cpp_info.libdirs)
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.cpp_info.libs]
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-ldl"])
        cc = os.environ.get("CC", "clang")
        # C 测试不能收 C++ 标准开关（clang 报 not allowed with 'C'）；musl 上还要
        # 用 gnu 方言，严格 ISO 方言不定义 _POSIX_C_SOURCE，POSIX 函数不声明。
        self.run(f"{cc} -std=gnu99 test.c -o test_probe {' '.join(incs)} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
