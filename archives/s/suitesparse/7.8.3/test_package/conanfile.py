import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include 各子库公共头（依赖包 include/），
        # 又链接全部 7 个库（依赖包 lib/）——CI 的 L1e 破坏性反向验证两处都要真实依赖。
        incs, linkdirs, rpaths = [], [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            for p in _d.cpp_info.libdirs:
                if os.path.isdir(p):
                    linkdirs.append("-L" + p)
                    rpaths.append("-Wl,-rpath-link," + p)
        dep = self.dependencies["suitesparse"].cpp_info
        libs = " ".join("-l" + l for l in dep.libs)
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        self.run("{cc} test.c -o test_probe {inc} {ld} {rp} {libs} -lopenblas -lm".format(
            cc=cc, inc=" ".join(incs), ld=" ".join(linkdirs),
            rp=" ".join(rpaths), libs=libs))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} -c './test_probe'".format(bash), env="conanrun")
