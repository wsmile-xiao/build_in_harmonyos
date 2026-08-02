import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["net-snmp"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libnetsnmp.so")
        cc = os.environ.get("CC", "clang")
        # C 测试**不能**收 C++ 标准开关（clang 报 not allowed with 'C'）。
        # musl 上还要用 gnu 方言：严格 ISO 方言不定义 _POSIX_C_SOURCE，
        # POSIX 函数（clock_gettime 等）在 musl 头里就不声明。
        std_flag = "-std=gnu99"
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
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")

        # 消费方 ezsnmp 的 setup.py 靠 `net-snmp-config --version` / `--libs` 拿编译参数。
        # 这个脚本若没装出来、或装出来吐不出东西，ezsnmp **连构建都起不来**——
        # 而 C API 测试全绿也发现不了这一点（它压根不经过这个脚本）。
        cfg = os.path.join(self.dependencies["net-snmp"].package_folder, "bin", "net-snmp-config")
        self.run(f"{bash} -c '{cfg} --version'", env="conanrun")
        self.run(f"{bash} -c '{cfg} --libs'", env="conanrun")
