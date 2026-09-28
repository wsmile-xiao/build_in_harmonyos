#!/usr/bin/env python3
"""test_package for miruo — 真实执行被测包产物（R34）。

test() 运行：
  test_ohos.sh — 鸿蒙特有测试（9 条断言）：
    ELF64/AArch64/PIE、musl 解释器（/lib/ld-musl-aarch64.so.1）、
    无 RPATH/RUNPATH、动态依赖仅为 libc.so（libpcap 静态链入）、
    OHOS ELF 标记（.codesign/.note.ohos.ident）、Release 产物无本机
    构建路径泄漏、`miruo -V` 真实运行（版本串，注意上游缺陷打印
    0.9.6a）、`miruo -h` 优雅退出 rc=0、`miruo -i nonexist0` 报错
    退出 rc=1（错误接口诊断，证明 pcap_open_live 路径真实执行）。

OHOS 说明：/system/bin/sh 不能直接 exec ELF，脚本由 bash 包裹调用。
fail closed：任何非零退出/超时/缺工具都判失败，不跳过。
"""
import os
import shutil

from conan import ConanFile


class MiruoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["miruo"]
        bindir = os.path.join(dep.package_folder, "bin")
        binary = os.path.join(bindir, "miruo")
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged miruo not found: {binary}")

        # OHOS: /system/bin/sh 不能直接 exec ELF；必须用 bash 包裹脚本。
        # 解析顺序：CONFIG_SHELL（profile buildenv）→ PATH 查找 →
        # /data/service/hnp/bin/bash；三者都拿不到则 fail closed。
        # 用 os.path.isfile 而非 os.access(X_OK)：HMDFS 忽略 chmod，
        # X_OK 恒为 False（R49/E046）。
        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.isfile(bash)):
            bash = shutil.which("bash") or ""
        if not (bash and os.path.isfile(bash)):
            fallback = "/data/service/hnp/bin/bash"
            bash = fallback if os.path.isfile(fallback) else ""
        if not bash:
            raise FileNotFoundError(
                "bash not found for test scripts "
                "(set CONFIG_SHELL or put bash on PATH)"
            )

        # 鸿蒙特有测试（平台特性 + 真实运行行为）
        self.run(
            f'"{bash}" test_ohos.sh "{binary}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        self.output.info("miruo: OHOS tests OK (9 assertions)")
