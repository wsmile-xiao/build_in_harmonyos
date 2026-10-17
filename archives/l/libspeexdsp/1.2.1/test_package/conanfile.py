import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libspeexdsp"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0] if dep.libdirs else os.path.join(
            self.dependencies["libspeexdsp"].package_folder, "lib")
        cc = os.environ.get("CC", "clang")
        # 消费者视角：重采样 API 真实调用（init→process_int→destroy 全链路）
        self.run(f"{cc} test.c -o test_speexdsp {inc} -L{libdir} -lspeexdsp -lm")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_speexdsp'", env="conanrun")
