import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["jbig2dec"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        if not dep.libdirs:
            raise ConanInvalidConfiguration("jbig2dec package does not provide a library directory")
        libdir = dep.libdirs[0]
        # R33：从 Conan Toolchain 获取编译器，禁止裸用 os.environ。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        self.run(f'{cc} test.c -o test_probe {inc} -L"{libdir}" -ljbig2dec')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
