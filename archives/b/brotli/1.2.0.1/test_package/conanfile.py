import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["brotli"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)

        # **直接链接**，不用 dlopen 探针：
        #   · dlopen+dlsym 只证明「文件在、导出了某个名字」，不证明任何功能可用；
        #   · 且原占位只 dlopen 了 libbrotlidec.so，libbrotlienc 根本没被碰过。
        # 这里三个组件库全链上，编解码往返才测得动。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(
            ["-L" + p for p in libdirs]
            + ["-lbrotlienc", "-lbrotlidec", "-lbrotlicommon"]
            # 运行期靠 conanrun 的 LD_LIBRARY_PATH 解析裸名 SONAME，
            # 不写 -rpath：rpath 会把构建机绝对路径烤进产物（本仓 SONAME 事故同源）
        )
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        ldpath = os.pathsep.join(
            p for _ref, _d in self.dependencies.items() for p in _d.cpp_info.libdirs)
        # 显式给库搜索路径：brotli 按 shared 发布，但 VirtualRunEnv 对某些包不写
        # LD_LIBRARY_PATH（实测 conanrunenv-*.sh 里是空的 for 循环），
        # 而补了 SONAME 之后 DT_NEEDED 是裸名，必须有搜索路径才找得到。
        old = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ldpath + (os.pathsep + old if old else "")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
