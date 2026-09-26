import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["freetype"].cpp_info
        # 头闭包自检用「所有依赖」的 include
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libfreetype.so")
        # R33: 编译器不裸用可能为空的 shell 变量——从 conan conf 取编译器字典
        # （E307/E529: self.conf.get("tools.build:compiler_executables", default={},
        # check_type=dict)；2.29.1 只注册父级 key，子 key ':c' 未注册直接 get 会报
        # "does not exist in configuration list"）。profile 的 [conf] 已注入 c/cpp，
        # 再回退 PATH 上的 clang（profile buildenv 保证 /data/service/hnp/bin 在 PATH）
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or os.environ.get("CC", "clang")
        # 真实链接 libfreetype（R34：test 必须链接并调用被测包 API，
        # 破坏性 L1e 校验在 lib/ 被移走时链接/运行必然失败）
        self.run(f"{cc} test.c -o test_probe {inc} -L{libdir} -lfreetype "
                 f"-DTARGET_SO='\"{so}\"'")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
