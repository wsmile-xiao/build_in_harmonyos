import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libavif"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libavif.so")
        cc = os.environ.get("CC", "clang")
        # **必须把 profile 的 cppstd 传下去**：库本体是按它编的，
        # 测试若用编译器默认标准，会比库低，于是库头文件里的新标准设施全报找不到。
        # 实测 pinocchio 4.1.0（cppstd=17）：裸 clang++ 编测试时报
        # std::void_t / std::is_arithmetic_v / std::is_base_of_v / std::is_fundamental_v 不存在
        # ——看着像库坏了，其实是测试的标准不够。
        # C 测试不能收 C++ 标准开关；musl 上要 gnu 方言
        # （严格 ISO 不定义 _POSIX_C_SOURCE，POSIX 函数在 musl 头里不声明）。
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
