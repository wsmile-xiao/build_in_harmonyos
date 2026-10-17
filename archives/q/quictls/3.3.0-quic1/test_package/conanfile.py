#!/usr/bin/env python3
"""Conan test_package for quictls 3.3.0-quic1 — Conan L1 官方测试。

直接编译 + 运行，验证：
  1) 加密核心（SHA-256 / AES-256-GCM / EC P-256 / RAND / TLS1.3 / X509）
  2) QUIC-TLS provider API（BoringSSL 兼容，本配方启用的 QUIC 特性）
     —— 对被测包的实质依赖（R34）：未带 QUIC 构建的包会因符号缺失链接失败。
CI 通过 `conan create` 自动执行本 test_package。
"""
import os
import shlex

from conan import ConanFile


class QuictlsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against quictls from Conan package
        dep = self.dependencies["quictls"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        sys_flags = " ".join(f"-l{l}" for l in cpp.system_libs)
        # R49: test_package 编译时同样需要 LD_LIBRARY_PATH 让 lld 找到 libxml2.so.16
        # 参考主包 conanfile.py 的 build() 处理
        # R33: 对齐主配方编译器解析链（conan conf > 环境 CC > 默认），
        # 避免 Conan 工具链注入编译器时 test_package 回退到 PATH 裸查找（检视 P3-2）
        cc_conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = cc_conf.get("c") or os.environ.get("CC") or "clang"
        ld_env = (
            "LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            ":/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/sysroot/usr/lib"
            ":${LD_LIBRARY_PATH:-}"
        )
        self.run(f"{ld_env} {shlex.quote(cc)} test_quictls.c -o test_quictls {inc_flags} {lib_flags} {link_flags} {sys_flags}")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution. Try CONFIG_SHELL first,
        # then fall back to common bash locations.
        bash = os.environ.get("CONFIG_SHELL", "")
        if not bash or not os.path.exists(bash):
            bash = ""
            for candidate in ["/data/service/hnp/bin/bash",
                              "/storage/Users/currentUser/usr/local/bin/bash",
                              "/usr/bin/bash", "/bin/bash"]:
                if os.path.exists(candidate):
                    bash = candidate
                    break
        if bash:
            self.run(f"{bash} -c './test_quictls'", env="conanrun")
        else:
            self.run("./test_quictls", env="conanrun")
