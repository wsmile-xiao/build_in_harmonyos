#!/usr/bin/env python3
"""Conan test_package — libideviceactivation 1.1.1（Conan L1 官方测试）。

用例组成：

A. 消费者 API 测试（CMake + test.c，真实调用被测包 API）
   - libplist 路径：请求字段 dict set/get 往返、get_fields 返回 plist dict
   - libcurl 路径：DRM handshake 请求创建 + 默认激活服务 URL
   - libxml2 路径：HTML 响应解析 + XPath 判定 isAuthRequired
   - 鸿蒙特有断言：运行时 sysname == HarmonyOS / machine == aarch64

B. 鸿蒙特有用例（OHOS-specific，Linux 上必然失败，故仅对 OHOS 生效）
   - OHOS-1 `ohos_elf_interp`：打包产出的 `ideviceactivation` 必须嵌入
     OHOS musl 动态加载器 `/lib/ld-musl-aarch64.so.1`
     （glibc/Linux 目标会嵌入 `/lib64/ld-linux-*`，因此该断言只对 OHOS 成立）
   - OHOS-2 `ohos_runtime_closure`：在 Conan 运行时环境（env="conanrun"）下真实
     执行 `ideviceactivation --version` 且退出码为 0 并输出正确版本号
     —— 等价于校验 libcurl.so / libxml2.so.16 等 OHOS 共享依赖的加载闭包完整
     （这是本次适配的 core 风险点：libxml2 的 SONAME `libxml2.so.16` 与
     OHOS SDK 工具链自带的 `native/llvm/lib/libxml2.so.16` 同名，必须由
     Conan 包的 lib 目录优先解析）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibideviceactivationTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # ── A. 消费者 API 测试（真实编译 + 执行被测包 API）──
        # env="conanrun": 测试程序动态链接 libcurl.so / libxml2.so.16，
        # OHOS 加载器无 conan 缓存 lib 的默认搜索路径，必须注入运行时环境。
        cmake = CMake(self)
        cmake.test(env="conanrun")

        # ── B. 鸿蒙特有用例 ──
        dep = self.dependencies[self.tested_reference_str]
        cli = os.path.join(dep.cpp_info.bindirs[0], "ideviceactivation")
        self.output.info(f"OHOS test: packaged CLI = {cli}")

        # OHOS-1: ELF interp 必须是 OHOS musl 加载器（纯 Python 读取，不依赖外部工具）
        with open(cli, "rb") as fh:
            blob = fh.read()
        if b"/lib/ld-musl-aarch64.so.1" not in blob:
            raise ConanException(
                "OHOS case 'ohos_elf_interp' FAILED: packaged ideviceactivation is not "
                "an OHOS aarch64 ELF (missing /lib/ld-musl-aarch64.so.1 interpreter)")
        self.output.info("OHOS case 'ohos_elf_interp': OK (aarch64 OHOS musl loader)")

        # OHOS-2: 运行时闭包 —— 真实执行 CLI，要求 libcurl/libxml2 等共享依赖全部可解析
        out_file = os.path.join(self.build_folder, "ohos-cli-version.txt")
        self.run(f'"{cli}" --version > "{out_file}"', env="conanrun")
        with open(out_file, encoding="utf-8") as fh:
            version_out = fh.read().strip()
        self.output.info(f"OHOS test: `ideviceactivation --version` -> {version_out!r}")
        if "ideviceactivation 1.1.1" not in version_out:
            raise ConanException(
                "OHOS case 'ohos_runtime_closure' FAILED: unexpected --version output "
                f"{version_out!r}")
        self.output.info("OHOS case 'ohos_runtime_closure': OK (all NEEDED libs resolved)")
