#!/usr/bin/env python3
"""Conan recipe — quictls 3.3.0-quic1 (OpenSSL 3.3.0 + QUIC-TLS 1.3, custom-perl build).

quictls = quictls 项目官方维护的 OpenSSL fork（2025-04-10 归档，后继仓库 quictls/quictls）。
3.3.0-quic1 = OpenSSL 3.3.0 + QUIC-TLS 1.3 扩展。

本版本 = 首次适配上游 3.3.0-quic1 到鸿蒙 PC（OHOS aarch64），无 .N 后缀（R37 首次适配=上游版本号）。

关键决策（W0b 对齐已合并 openssl/3.5.8.1 配方 + 带实测证据的偏离）：
  - CC=clang 显式（openssl Configure 默认 gcc，本机无 gcc）
  - --with-rand-seed=getrandom 排除 DEVRANDOM_WAIT/FD_SET 路径（E235；3.3.0 实测 configdata 0 次 DEVRANDOM）
  - no-asm no-shared（R26：openssl 为系统同名库，静态构建避免 .so 污染 /lib）
  - make build_sw -j2（对齐 3.5.8.1；OOM 回退 -j1）
  - LD_LIBRARY_PATH 显式注入 OHOS SDK llvm/lib（lld 找 libxml2.so.16）

  W0b 偏离 3.5.8.1（证据见 notes.md，R1 参数最少化）：
  - 不加 -D__MUSL__、不带 3.5.x FD_SET 有界补丁：3.3.0 在
    --with-rand-seed=getrandom 排除 DEVRANDOM FD_SET 路径后，其余 FD_SET 使用
    （speed.c job 调度）在 OHOS SDK 上链接无虞（实测：libcrypto/libssl + openssl
    CLI + 300+ 测试二进制全部产出，0 链接错误）。3.5.x 补丁直接移植反而编译失败：
    有界实现依赖 ossl_inline，3.3.0 sockets.h 未包含 macro.h → sockets.h:212 报错。
  - 补丁机制（export/apply_conandata_patches）保留为 no-op 形态：conandata 无 patches
    （G1 门禁要求机制存在；未来 .N 修订如需补丁，直接补 conandata 即可）。

QUIC 特性选型（本配方核心 delta，路径 B 知识增量）：
  - 采用默认 boring-quic-api（不传 enable-quic）
  - 依据：
    1) libmsquic 2.5.7（已合并）vendored quictls configure = 裸 `Configure linux-aarch64`
       （默认特性）——生态消费的 QUIC-TLS API 即 BoringSSL 兼容 API
    2) 原生 `quic` 栈特性（OSSL_QUIC_* API）与 boring-quic-api 互斥
       （Configure L1221 die: "boring-quic-api and quic are incompatible options"）
    3) 3.3.0-quic1 原生栈在 70-test_quic_{tserver,multistream} 有 2 个确定性上游缺陷
       （quic_tls.c:768 扩展注册 INTERNAL_ERROR，与平台无关）→ 本次不启用
    4) 生态外部 QUIC 栈（msquic/lsquic）均需要 BoringSSL 兼容 API
       （SSL_set_quic_method / SSL_provide_quic_data / SSL_set_quic_transport_params）
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class QuictlsConan(ConanFile):
    name = "quictls"
    version = "3.3.0-quic1"
    description = "OpenSSL 3.3.0 + QUIC-TLS 1.3 extension (quictls fork, BoringSSL-compatible QUIC-TLS API)"
    license = "Apache-2.0"
    homepage = "https://github.com/quictls/openssl"
    url = "https://github.com/quictls/openssl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        # R26: openssl 为系统同名库，本配方仅静态构建（no-shared）。
        # 显式请求 shared=True 时 fail-fast，而非静默产出静态包（检视 P2-1：
        # 否则同一配方按不同选项产出内容相同但 package ID 不同的包，接口契约违约）
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "quictls/3.3.0-quic1 only supports static builds (no-shared, R26)")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # quictls 是自包含的加密/QUIC-TLS 库，无外部 Conan 依赖
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_target(self):
        # 3.3.0 自带 linux-aarch64 配置，无需自定义 config
        if self.settings.arch in ("armv8", "aarch64"):
            return "linux-aarch64"
        if self.settings.arch == "x86_64":
            return "linux-x86_64"
        raise Exception(f"Unsupported arch: {self.settings.arch}")

    def build(self):
        apply_conandata_patches(self)

        # R32: settings.os 判断必须 `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        prefix = self.package_folder
        openssldir = os.path.join(prefix, "ssl")

        # R33: 编译器必须来自 Conan conf/recipe 常量，不能裸用 shell ${CC}。
        # openssl Configure 默认选 "gcc"（本机无），必须显式传 CC=clang。
        cc_conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = cc_conf.get("c") or os.environ.get("CC") or "clang"

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

        # -j2 并行编译（对齐已合并 openssl/3.5.8.1 配方；OOM 回退 -j1）
        # OHOS Worker lld 链接器依赖 libxml2.so.16（位于 llvm/lib），
        # 显式设置 LD_LIBRARY_PATH，否则 test/*.so 链接阶段 lld 报
        # "Error relocating ... xmlFreeDoc: symbol not found"。
        # ${LD_LIBRARY_PATH:-} 兼容 CI 默认无该变量的情况。
        ld_env = (
            "LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            ":/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/sysroot/usr/lib"
            ":${LD_LIBRARY_PATH:-}"
        )
        self.run(f"{ld_env} make build_sw -j2", cwd=self.source_folder)

    def package(self):
        # make install_sw 仅装软件（无 docs）。
        # OpenSSL 3.3.x 源码 doc 生成缺部分 pod.in 文件，`make install` 会失败，install_sw 跳过 docs。
        self.run("make install_sw", cwd=self.source_folder)

    def package_info(self):
        # quictls 提供 libcrypto 与 libssl（与 openssl 同名库，静态 .a 构建，R26）
        self.cpp_info.libs = ["ssl", "crypto"]
        # 包同时交付 openssl/c_rehash CLI（install_sw → bin/），声明为 CLI 包（R38，与软件级 commands.json 自洽）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["dl", "pthread"]
        # Expose the openssl CLI（version 字符串: OpenSSL 3.3.0+quic）
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
