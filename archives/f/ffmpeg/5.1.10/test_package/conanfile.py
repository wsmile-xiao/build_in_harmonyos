import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["ffmpeg"].cpp_info
        # 头闭包自检要用「所有依赖」的 include
        incs = []
        for _ref, _d in self.dependencies.items():
            # 只取绝对路径：带 components 的依赖其根 cpp_info.includedirs 可能仍是相对的 "include"，
            # 拼进编译命令没有意义（日志里会出现一串 -Iinclude）。
            incs += ["-I" + p for p in _d.cpp_info.includedirs if os.path.isabs(p)]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "/data/service/hnp/bin/clang")
        # 【直接链库，不用 dlopen】R34 要求 test 实际调用被测包 API（仅 dlsym 解析不达标）；
        # R40 对多媒体类另要求覆盖平台相关功能而非仅 version()。故本 test 真跑编码。
        # 且 CI 的 L1e 会把包的 lib/ 与 include/ 移走后重跑 conan test，直链使其在
        # 编译/链接期就失败，反向验证更硬。
        self.run(
            f"{cc} test.c -o test_probe {inc} -L{libdir} "
            f"-lavfilter -lavformat -lavcodec -lswscale -lswresample -lavutil -lm"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
