import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libopus"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0] if dep.libdirs else os.path.join(
            self.dependencies["libopus"].package_folder, "lib")
        so = os.path.join(libdir, "libopus.so")
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -ldl")
        # HarmonyOS 专项：编码/解码真实回环（链接 libopus.so 而非仅 dlopen）
        self.run(f"{cc} test_ohos_roundtrip.c -o test_roundtrip {inc} "
                 f"-L{libdir} -lopus -lm")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
        self.run(f"{bash} -c './test_roundtrip'", env="conanrun")
