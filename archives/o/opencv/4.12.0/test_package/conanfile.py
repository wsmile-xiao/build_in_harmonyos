import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["opencv"].cpp_info
        # 直接编译+链接（非 dlopen）：既 #include OpenCV 公共头（依赖包的 include/），
        # 又链接 opencv_* 共享库（依赖包的 lib/）——CI 的 L1e 破坏性反向验证会把这两个目录
        # 整个移走再跑一次，两处都真实依赖才不会被判成假测试。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]

        # OpenCV 各 .so 自身 NEEDED 了 ffmpeg/png/jpeg/webp 等依赖的库，链接期须能解析到它们
        linkdirs, rpaths = [], []
        for _ref, _d in self.dependencies.items():
            for p in _d.cpp_info.libdirs:
                if os.path.isdir(p):
                    linkdirs.append("-L" + p)
                    rpaths.append("-Wl,-rpath-link," + p)

        libs = " ".join("-l" + l for l in dep.libs)
        cxx = self.conf.get("tools.build:compiler_executables", default={},
                            check_type=dict).get("cpp", "clang++")
        self.run("{cxx} -std=c++17 test.cpp -o test_probe {inc} {ld} {rp} {libs} "
                 "-ldl -lm -lpthread".format(
                     cxx=cxx, inc=" ".join(incs), ld=" ".join(linkdirs),
                     rp=" ".join(rpaths), libs=libs))
        self.output.info("test_probe 已链接 OpenCV：libdir=%s" % dep.libdirs[0])

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
