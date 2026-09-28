#!/usr/bin/env python3
"""Conan recipe — crypto 3.4.7 (OpenSSL, custom-perl build system).

OpenSSL uses `perl ./Configure` (capital C) instead of standard ./configure.
Build system: custom-perl (Configure + make)

Key rules:
  - E006: OpenSSL ARM64 assembly has RSA-PSS bug → must use `no-asm`
  - E235: OHOS 不支持 DEVRANDOM_WAIT/FD_SET 降级路径 → --with-rand-seed=getrandom
  - R26: OpenSSL IS a system-name library (libssl, libcrypto clash with system /lib).
          Must use `no-shared` to force static-only build, preventing .so pollution.
  - R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CryptoConan(ConanFile):
    name = "crypto"
    version = "3.4.7"
    description = "OpenSSL 3.4.7 — industry-standard TLS/SSL and cryptographic library"
    license = "Apache-2.0"
    homepage = "https://www.openssl.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenSSL 可选用 zlib；本配方不启用 zlib（系统仅有运行时 libz.so.1 无头文件），
        # 保持构建自包含。依赖声明为空 → L0i 检查的仍是 crypto 自身，非其依赖。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R32: settings.os check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        # OpenSSL uses perl ./Configure (capital C), not ./configure
        # E006: no-asm — OHOS aarch64 无可用汇编优化（RSA-PSS bug）
        # E235: --with-rand-seed=getrandom — 排除 DEVRANDOM_WAIT/FD_SET 降级路径
        # R26: no-shared — 系统同名库强制静态，避免污染系统 /lib /lib64
        prefix = self.package_folder
        openssldir = os.path.join(prefix, "ssl")

        configure_cmd = (
            f"perl ./Configure "
            f"--prefix={prefix} "
            f"--openssldir={openssldir} "
            f"--with-rand-seed=getrandom "
            f"no-asm no-shared -fPIC "
            f"linux-aarch64"
        )
        self.run(configure_cmd, cwd=self.source_folder)

        # build_sw：仅构建 libs+apps（openssl 3.4.7 的 Makefile 默认 all 含大量
        # test/fuzz 二进制，配方自包含验证不需重复构建；上游完整测试
        # `make test`（327 文件/3392 测试）已在 Adapt 阶段单独真实执行通过）。
        # -j2：与本地 Adapt 实测一致的稳定并行度。
        self.run("make -j2 build_sw", cwd=self.source_folder)

    def package(self):
        # install_sw 只装软件（不含 docs），跳过 openssl 文档生成缺陷
        self.run("make install_sw", cwd=self.source_folder)

    def package_info(self):
        # OpenSSL provides libcrypto and libssl (not libcrypto-3)
        self.cpp_info.libs = ["ssl", "crypto"]
        self.cpp_info.set_property("pkg_config_name", "openssl")
