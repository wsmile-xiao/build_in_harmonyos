import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include 公共头（dieharder include/ + gsl include/），
        # 又链接 libdieharder/libgsl/libgslcblas——CI 的 L1e 会把包的 include/、lib/ 移走
        # 再跑一次，两处都必须真实依赖才会在被破坏时失败。
        incs, linkdirs = [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            linkdirs += [p for p in _d.cpp_info.libdirs if os.path.isdir(p)]
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        link = " ".join(["-L" + p for p in linkdirs]
                        + ["-Wl,-rpath-link," + p for p in linkdirs])
        self.run("{cc} test.c -o test_probe {inc} {link} -ldieharder -lgsl -lgslcblas -lm".format(
            cc=cc, inc=" ".join(incs), link=link))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 本设备 HNP bash 的 getcwd() 在 spawn 时的 cwd 上不可靠；cd 按名进入后
        # bash 恢复正常（pwd 内建可用）。python 侧 getcwd 可靠，取绝对路径传给 cd。
        cwd = os.getcwd()
        bindir = self.dependencies["dieharder"].cpp_info.bindirs[0]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # ① 探针：链接 libdieharder 的真实计算断言（test.c）
        self.run("{bash} -c 'cd {cwd} && ./test_probe'".format(bash=bash, cwd=cwd),
                 env="conanrun")
        # 上游没有 automake check 目标（顶层/子目录 Makefile.am 均无），
        # dieharder 的官方测试入口就是它自己的 CLI：
        # ② -l 冒烟：列出全部内置测试模块（上游 31 项，应完整列出）
        self.run("{bash} -c 'cd {cwd} && {bindir}/dieharder -l'".format(
            bash=bash, cwd=cwd, bindir=bindir), env="conanrun")
        # ③ 固定种子（-S 42）单测试真实运行子集（快测试 ×3）：
        #    -d 0 Diehard_Birthday / -d 2 Diehard_Rank_32x32 / -d 13 Diehard_Squeeze
        self.run("{bash} -c 'cd {cwd} && {bindir}/dieharder -d 0 -p 3 -S 42'".format(
            bash=bash, cwd=cwd, bindir=bindir), env="conanrun")
        self.run("{bash} -c 'cd {cwd} && {bindir}/dieharder -d 2 -p 3 -S 42'".format(
            bash=bash, cwd=cwd, bindir=bindir), env="conanrun")
        self.run("{bash} -c 'cd {cwd} && {bindir}/dieharder -d 13 -p 3 -S 42'".format(
            bash=bash, cwd=cwd, bindir=bindir), env="conanrun")
