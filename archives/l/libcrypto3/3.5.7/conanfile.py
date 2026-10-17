#!/usr/bin/env python3
"""Conan recipe — libcrypto3 3.5.7 (OpenSSL libcrypto component, standalone packaging).

libcrypto3 = OpenSSL source built with only libcrypto exposed.
Unlike the full openssl package which exports both ssl + crypto,
libcrypto3 exports only the crypto library — for consumers that need
cryptographic primitives (AES/RSA/SHA/HMAC) without TLS/SSL.

OpenSSL uses `perl ./Configure` (capital C) instead of standard ./configure.
Build system: custom-perl (Configure + make)

Key rules:
  - R9:  Use make -j2 (bounded parallelism; -j$(nproc) may OOM on constrained CI)
  - R26: libcrypto IS a system-name library (clashes with system /lib/libcrypto).
          Must build static-only (`no-shared`) to prevent .so pollution.
  - R32: settings.os check uses `in ("Linux", "OHOS")` (not `== "Linux"`).
  - R39: Source URL points to official GitHub release (CI auto-adds mirrors).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Libcrypto3Conan(ConanFile):
    name = "libcrypto3"
    version = "3.5.7"
    description = "OpenSSL libcrypto component — cryptographic primitives library (AES/RSA/SHA/HMAC)"
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
        # libcrypto has no external dependencies for a functional static build.
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

        # R33: compiler must come from Conan conf/recipe constants, not shell ${CC}.
        # openssl Configure defaults to "gcc" (no gcc on this machine), must pass CC=clang.
        cc_conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = cc_conf.get("c") or os.environ.get("CC") or "clang"
        # OHOS(musl) does not provide __fd_chk; patch 0002's openssl_fdset
        # bounded implementation depends on -D__MUSL__ to activate.
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
        self.run(configure_cmd, cwd=self.source_folder)

        # R9: -j2 bounded parallelism for W3 time budget.
        # OHOS Worker lld linker needs libxml2.so.16 (in llvm/lib).
        ld_env = (
            "LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            ":/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/sysroot/usr/lib"
            ":${LD_LIBRARY_PATH:-}"
        )
        self.run(f"{ld_env} make build_sw -j2", cwd=self.source_folder)

    def package(self):
        # make install_sw installs software only (no docs) to --prefix.
        # OpenSSL 3.5.x source is missing some pod.in files so
        # `make install` fails during doc generation; install_sw skips docs.
        self.run("make install_sw", cwd=self.source_folder)

    def package_info(self):
        # libcrypto3 exports ONLY libcrypto (not libssl).
        # This is the key difference from the openssl package.
        self.cpp_info.libs = ["crypto"]
        self.cpp_info.system_libs = ["dl", "pthread"]
