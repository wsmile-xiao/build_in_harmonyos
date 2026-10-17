#!/usr/bin/env python3
"""Conan recipe — OpenSSL 3.5.6.1.1 (custom-perl build system).

3.5.6.1.1 = 3.5.6 + 适配修复（R37）：
  - build() 显式传 CC=clang（openssl Configure 默认选 gcc，本机无 gcc → 编译失败）
  - 继承 3.5.6.1 的 __fd_chk 平台补丁（0001/0002），并用 --with-rand-seed=getrandom 规避
    OHOS(musl) 不提供 __fd_chk 导致的 RAND 消费者链接失败
  - 去掉模板残留，直接基于 custom-perl 流程

OpenSSL uses `perl ./Configure` (capital C) instead of autotools ./configure.
Build system: custom-perl (Configure + make)

Key rules:
  - R9:  Use make -j2 (bounded parallelism; -j$(nproc) may OOM on constrained CI)
  - R26: OpenSSL is a system-name library (libssl/libcrypto clash with system /lib).
          Must build static-only (`no-shared`) to prevent .so pollution.
  - R32: settings.os check uses `in ("Linux", "OHOS")` (not `== "Linux"`).
  - R39: Source URL points to official GitHub release (CI auto-adds mirrors).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class OpensslConan(ConanFile):
    name = "openssl"
    version = "3.5.6.1.1"
    description = "Industry-standard TLS/SSL and cryptographic library"
    license = "Apache-2.0"
    homepage = "https://www.openssl.org/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenSSL can optionally use zlib for compression, but no dependency
        # is required for a functional static build.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_target(self):
        # 3.5.x ships a built-in linux-aarch64 config; no custom config needed.
        if self.settings.arch in ("armv8", "aarch64"):
            return "linux-aarch64"
        if self.settings.arch == "x86_64":
            return "linux-x86_64"
        raise Exception(f"Unsupported arch: {self.settings.arch}")

    def build(self):
        apply_conandata_patches(self)

        # R32: settings.os check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        prefix = self.package_folder
        openssldir = os.path.join(prefix, "ssl")

        # R33: 编译器必须来自 Conan conf/recipe 常量，不能裸用 shell ${CC}。
        # openssl Configure 默认会选 "gcc"（本机无 gcc），必须显式传 CC=clang。
        cc_conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = cc_conf.get("c") or os.environ.get("CC") or "clang"
        # OHOS(musl) 不提供 __fd_chk；patch 0002 的 openssl_fdset 有界实现依赖
        # -D__MUSL__ 激活，否则会回退到裸 FD_SET 并在链接期失败。
        if self.settings.os == "OHOS":
            cc = f"{cc} -D__MUSL__"

        configure_cmd = (
            f"perl ./Configure "
            f"--prefix={prefix} "
            f"--openssldir={openssldir} "
            f"no-asm "
            f"no-shared "
            f"--with-rand-seed=getrandom "
            f'CC="{cc}" '
            f"{self._configure_target()}"
        )
        # Run from source folder where Configure script exists
        self.run(configure_cmd, cwd=self.source_folder)

        # R9: -j2 并行编译以在 W3 600s 窗口内完成（OOM 则退回 -j1）
        self.run("make build_sw -j2", cwd=self.source_folder)

    def package(self):
        # make install_sw installs software only (no docs) to --prefix.
        # OpenSSL 3.5.6 source is missing some pod.in files (e.g. openssl-spkac.pod.in)
        # so `make install` fails during doc generation; install_sw skips docs.
        self.run("make install_sw", cwd=self.source_folder)

    def package_info(self):
        # OpenSSL provides libcrypto and libssl (not libopenssl)
        self.cpp_info.libs = ["ssl", "crypto"]
        # Add -ldl -pthread for linking
        self.cpp_info.system_libs = ["dl", "pthread"]
        # Expose the openssl CLI
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
