import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libxlsxwriter"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        cc = os.environ.get("CC", "clang")
        # C test, gnu99 dialect for musl POSIX decls (libzip test_package 同款)
        std_flag = "-std=gnu99"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # 所有依赖的库都要链（zlib 是 xlsxwriter 的链接闭包，test.c 自己也用 inflate）
        all_libs = []
        for _ref, _d in self.dependencies.items():
            all_libs += list(_d.cpp_info.libs)
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in all_libs]
                        + ["-Wl,-rpath," + p for p in libdirs])
        self.run(f"{cc} {std_flag} test.c -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
