#!/usr/bin/env python3
"""test_package — dwarves 1.30 L1 官方测试 (conan create 自动执行)。

验证：
1. 消费者用例: 仅通过已安装的公开头文件(dwarves.h)/公开 API + libdwarves
   链接目标，编译、链接、运行，验证一家真实第三方使用者能否消费该库。
   dwarves.h 第 14 行直接 #include <obstack.h>（OHOS-musl 由 musl-obstack 提供），
   因此消费者须在 requirements 中显式声明该垫片依赖（CMakeDeps 不为传递依赖
   生成 config 文件，库的 cpp_info.requires 不展开为消费者的 find_package）。
2. CLI 可执行: pahole 可运行并输出版本（真实业务语义）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
from conan.tools.files import save, copy


class DwarvesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # dwarves.h（dwarves 公开头）依赖的 OHOS-musl 垫片头与 libdw/libelf 头
        self.requires("musl-obstack/1.2.3")
        self.requires("argp-standalone/1.5.0")
        self.requires("elfutils/0.195")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cpp = self.dependencies[self.tested_reference_str].cpp_info
        bindir = cpp.bindirs[0]
        if can_run(self):
            # 消费者用例：消费 dwarves 公开 API 的可执行程序
            consumer = os.path.join(self.cpp.build.bindirs[0], "consumer_dwarves")
            self.run(f"{consumer}", env="conanrun")
            self.output.info("✓ 消费者用例执行成功（公开 API 编译/链接/运行）")

            # CLI 可执行：pahole --version（调用者视角验证）
            pahole = os.path.join(bindir, "pahole")
            self.run(f"{pahole} --version", env="conanrun")
            self.output.info("✓ pahole CLI 可运行")

            # 鸿蒙专项测试：clang --target=bpf 生成带 BTF 的对象，pahole -F btf
            # 解析出结构体类型（dwarves 的 BTF 读取/类型打印链路在 OHOS aarch64 验证）
            import subprocess
            tmp = os.path.join(self.build_folder, "ohos-btf")
            os.makedirs(tmp, exist_ok=True)
            sample = os.path.join(self.source_folder, "ohos_btf_sample.c")
            obj = os.path.join(tmp, "sample.o")
            clang = "/data/service/hnp/bin/clang"
            r = subprocess.run([clang, "--target=bpf", "-c", "-g", "-O0", "-x", "c",
                                sample, "-o", obj],
                               capture_output=True, text=True)
            self.output.info(f"[ohos-btf] clang rc={r.returncode}")
            if r.returncode != 0:
                raise SystemExit(f"ohos-btf clang failed: {r.stderr[:500]}")
            self.run(f"{pahole} -F btf {obj}", env="conanrun")
            self.output.info("✓ 鸿蒙专项测试通过：pahole 解析 BTF 类型成功")