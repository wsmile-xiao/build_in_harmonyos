import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # C++ 库必须**直接链接**（-lfreeimage），不能用 dlopen 探针：
        #   ① dlopen+dlsym 只解析不调用，达不到 R34 的门槛；
        #   ② 直接链接同时踩住 L1e 的两头 —— #include 依赖包的 include/，链接依赖包的 lib/，
        #      任一被 mv 走都会失败，反向验证不会误判为「假测试」。
        dep = self.dependencies["freeimage"].cpp_info
        incs = []
        libdirs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libdirs += ["-L" + p for p in _d.cpp_info.libdirs]
        cxx = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("cpp", "/data/service/hnp/bin/clang++")
        rpath = " ".join("-Wl,-rpath," + p for p in dep.libdirs)
        self.run(
            '"{cxx}" -std=c++17 test.cpp -o test_freeimage {inc} {libdir} '
            "-lfreeimage {rpath}".format(
                cxx=cxx, inc=" ".join(incs), libdir=" ".join(libdirs), rpath=rpath
            )
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_freeimage'", env="conanrun")
