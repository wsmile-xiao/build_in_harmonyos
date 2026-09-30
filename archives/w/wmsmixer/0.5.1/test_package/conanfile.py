#!/usr/bin/env python3
"""Conan test_package — wmsmixer 0.5.1 L1 冒烟测试 (R34 真实消费者用例 + L0c 测试源).

wmsmixer 为 X11 GUI dockapp（OHOS 无显示环境无法运行 GUI 本体），但其
--version 参数在 X 连接前即打印版本并 exit(0)，可作为端到端消费者用例。
test.c 做两项真实校验：
  1. 读取安装产物 wmsmixer 二进制，校验 arm64 ELF（magic + e_machine）；
  2. 执行 `wmsmixer --version`，验证退出码 0 且输出含版本 0.5.1。
手动编译 test.c 为 test_wmsmixer，test() 用 self.run() 执行（满足 L0c 测试源
+ L0d self.run 门禁；不依赖 CMakeToolchain 生成器，避免 CMakePresets 问题）。

运行期动态库：wmsmixer 动态链接 libX11/libXpm/libXext（conan 依赖）与
libc++_shared.so（OHOS SDK 工具链运行时，不在 conan 管理范围）。test() 中
显式构造 LD_LIBRARY_PATH 注入依赖库目录 + SDK libc++ 目录，保证子进程可加载。
"""
import os

from conan import ConanFile


class WmsmixerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 手动编译测试源（test.c -> test_wmsmixer），注入 wmsmixer 二进制路径
        bin_path = os.path.join(self.dependencies["wmsmixer"].package_folder, "bin", "wmsmixer")
        self.output.info(f"wmsmixer binary: {bin_path}")
        cc = self._get_cc()
        self.run(
            f"{cc} -O2 -Wall test.c -o test_wmsmixer "
            f"-DWMSMIXER_BIN_PATH='\"{bin_path}\"'"
        )

    def _get_cc(self):
        # 从 Conan toolchain 配置（tools.build:compiler_executables）解析 C 编译器，
        # 未配置则按 settings.compiler 族映射，禁用裸 shell 环境变量回退（R33）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c")
        if cc:
            return cc
        f = self.settings.get_safe("compiler")
        if f == "clang":
            return "clang"
        if f == "gcc":
            return "gcc"
        raise RuntimeError(f"Unsupported compiler family: {f!r}")

    def test(self):
        # 构造运行期 LD_LIBRARY_PATH：依赖库目录 + OHOS SDK libc++ 运行时库
        ld_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            for libdir in dep.cpp_info.libdirs or []:
                p = os.path.join(dep.package_folder, libdir)
                if p not in ld_paths:
                    ld_paths.append(p)
        sdk_libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        if os.path.isdir(sdk_libcxx):
            ld_paths.insert(0, sdk_libcxx)
        self.output.info(f"test LD_LIBRARY_PATH: {':'.join(ld_paths)}")
        # L0d 门禁要求 test() 调用 self.run() 执行测试程序；
        # Conan 2 self.run() env 参数须为 list，这里直接注入 os.environ
        os.environ["LD_LIBRARY_PATH"] = ":".join(ld_paths)
        self.run("./test_wmsmixer")
