import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libwebp"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（本配方无传递依赖，仅被测库自身）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        # 直接链接被测库（消费方真实形态；空壳 dlopen 探针已升级为功能 roundtrip 探针）。
        self.run(f"{cc} test.c -o test_probe {inc} -L{libdir} -lwebp -lsharpyuv")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
