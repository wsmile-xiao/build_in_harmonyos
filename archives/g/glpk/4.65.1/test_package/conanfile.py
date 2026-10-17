import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 消费者用例：只通过已安装/导出的公开头文件（glpk.h、lpx.h）与公开链接目标
        # （-lglpk -llpx）使用该库，模拟 COIN-OR OsiGlpk 这类旧 API 上层消费者。
        incs, linkdirs, rpaths = [], [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            for p in _d.cpp_info.libdirs:
                if os.path.isdir(p):
                    linkdirs.append("-L" + p)
                    rpaths.append("-Wl,-rpath-link," + p)
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        # 官方 oldapi 兼容层中 lpx_main 引用 glp_main（该函数在 glpsol CLI 主程序内，
        # 不在 libglpk 库中）。本消费者用例不调用 lpx_main；liblpx.a 按函数切段编译
        # （-ffunction-sections），此处 --gc-sections 修剪未用入口，避免可执行文件
        # 携带 glp_main 未解析重定位。共享库消费者（如 OsiGlpk）缺省不受影响。
        self.run("{cc} test.c -o test_probe {inc} {ld} {rp} "
                 "-Wl,--gc-sections -lglpk -llpx -lm".format(
            cc=cc, inc=" ".join(incs), ld=" ".join(linkdirs), rp=" ".join(rpaths)))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} -c './test_probe'".format(bash), env="conanrun")
