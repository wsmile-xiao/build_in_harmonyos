import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libxml2"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        if not dep.libdirs:
            raise ConanInvalidConfiguration("libxml2 package does not provide a library directory")
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libxml2.so")
        cc = os.environ.get("CC") or "clang"
        self.run(f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
