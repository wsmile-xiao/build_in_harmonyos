import os
from conan import ConanFile
from conan.tools.build import cross_building


class ArgpStandaloneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # elfutils/0.195 同款模式：直接用 clang++ 编译消费者探针（不经 CMake），
        # 显式拼 include/lib 路径，静态链接 libargp.a。
        dep = self.dependencies["argp-standalone"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs])
        cc = os.environ.get("CXX", "clang++")
        # -static-libstdc++：把 libc++ 静态链进探针，运行期只依赖系统 libc.so，
        # 避免 OHOS 上 libc++_shared.so 搜索路径问题（test 阶段二进制未签名也可能
        # 触发加载限制——静态链 C++ 运行时后此问题不存在）。
        self.run(f"{cc} test.cpp -o test_probe -static-libstdc++ {inc} {link}")

    def test(self):
        # R34: 实际执行探针二进制，验证 argp_parse 命令行解析往返（非空壳测试）
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
