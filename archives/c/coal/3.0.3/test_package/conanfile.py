import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["coal"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        # eigen 这个 conan 包的 cpp_info.includedirs 只写了 "include"，
        # 而它的头实际在 include/eigen3/Eigen/... —— 被测库的公开头 #include <Eigen/Core>
        # 会因此找不到（coal/data_types.h 实测）。构建阶段没事（走 Eigen3 的 cmake target），
        # 只有这种裸编译器命令行才需要补。
        # 用 self.dependencies["eigen"] 直接取（对传递依赖也有效），
        # 遍历 .items() 在 test_package 里取不到它。
        try:
            _ei = self.dependencies["eigen"].package_folder
            for _sub in ("include/eigen3", "include"):
                _p = os.path.join(_ei, *_sub.split("/"))
                if os.path.isdir(_p):
                    incs.append("-I" + _p)
        except Exception as _e:
            self.output.warning("取 eigen include 失败（可能不是依赖）: %s" % _e)
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libcoal.so")
        cc = os.environ.get("CXX", "clang++")
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs])
        self.run(f"{cc} test.cpp -o test_probe {inc} -DTARGET_SO='\"{so}\"' {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
