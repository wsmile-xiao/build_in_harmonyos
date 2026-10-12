import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libdsm"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（bdsm.h 间接依赖 libtasn1 头）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libdsm.so")
        cc = os.environ.get("CC", "clang")
        # C 测试不能收 C++ 标准开关；musl 上要 gnu 方言
        # （严格 ISO 不定义 _POSIX_C_SOURCE，POSIX 函数在 musl 头里不声明）。
        # libdsm 头本身是纯 C（bdsm.h），gnu11 与库本体构建方言一致。
        std_flag = "-std=gnu11"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-ldl"])
        self.run(f"{cc} {std_flag} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
