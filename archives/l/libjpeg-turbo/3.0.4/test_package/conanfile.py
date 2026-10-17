import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libjpeg-turbo"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libjpeg.so")
        cc = os.environ.get("CC", "clang")
        # R34/R40：test.c 真实调用被测库 API（jpeg_std_error/jpeg_create_compress/... 全链路编解码）
        self.run(f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -L{libdir} -ljpeg -Wl,-rpath,{libdir} -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
