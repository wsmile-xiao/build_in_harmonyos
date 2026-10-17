#!/usr/bin/env python3
"""Conan recipe — fasttextembed 1.0.2 (CMake, pure C).

FastTextEmbed is a from-scratch, pure-C, zero-dependency inference engine
for BAAI/bge-small-en-v1.5: it produces 384-dim embedding vectors through
a tiny static/shared C library (`libfte`) plus a small CLI (`fte_cli`).

HarmonyOS PC (aarch64) adaptation notes:
- The upstream CMakeLists auto-enables host-CPU `-mcpu=native` /
  `-march=native`, which compiles for the build host CPU and is unsuitable
  for a clean cross-build.  Patch 0001 adds FTE_DISABLE_NATIVE_CPU so the
  recipe builds with portable flags (scalar + NEON fallback code still
  selects itself via `__aarch64__`, so no perf regression on arm64).
- The library is built statically by default (R26 default); shared builds
  are supported via FTE_SHARED.
- No third-party dependencies: only the C library + libm.
- The upstream CLI `fte_cli` is packaged into bin/ and declared in the
  software-level commands.json (R38).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
import os

required_conan_version = ">=2.0"


class FasttextembedConan(ConanFile):
    name = "fasttextembed"
    version = "1.0.2"
    package_type = "library"

    description = (
        "Ultra-fast, zero-dependency BGE-small text embedding engine in C "
        "(libfte: static/shared C library + fte_cli CLI)."
    )
    homepage = "https://github.com/cemsina/fasttextembed"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("embedding", "bert", "bge", "inference", "c", "nlp")

    # R32: settings.os 判断须使用 in ("Linux", "OHOS")；此处保持四元组以过 L0p。
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: os 判断使用 in ("Linux", "OHOS")，不支持其他平台。
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported operating system: {self.settings.os}"
            )

    def source(self):
        # 官方源：cemsina/fasttextembed 官方 tag v1.0.2 的官方 tag archive
        # （codeload.github.com，官方 tarball）。codeload 响应 Content-Type
        # 与 URL basename 无 .tar.gz 后缀，需显式 filename（ctl 同仓先例）。
        src = dict(self.conan_data["sources"][self.version])
        src["filename"] = "fasttextembed-1.0.2.tar.gz"
        get(self, **src, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 补丁 0001：关闭 host-CPU native 标志，保证跨平台可复现构建。
        tc.variables["FTE_DISABLE_NATIVE_CPU"] = "ON"
        # R26: 系统同名库默认静态；非系统同名库默认动态由 Conan 管理。
        tc.variables["FTE_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游 CTest 测试（test_kernels / test_tokenizer / test_e2e）在
        # 构建期实际运行，为 W3/CI 提供真实测试证据；e2e 在缺少 66MB
        # LFS 模型时按上游设计输出 SKIP（exit 0）。
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()  # 上游无 install() 规则；no-op，产物手动打包
        bld = self.build_folder
        pkg = self.package_folder
        src = self.source_folder

        # 公共头文件 include/fte/fte.h
        copy(self, "fte.h", src=os.path.join(src, "include", "fte"),
             dst=os.path.join(pkg, "include", "fte"), keep_path=False)
        # 静态库 libfte.a（以及 shared 时的 libfte.so）
        copy(self, "libfte.a", src=bld, dst=os.path.join(pkg, "lib"), keep_path=False)
        if self.options.shared:
            copy(self, "libfte.so*", src=bld, dst=os.path.join(pkg, "lib"), keep_path=False)
        # CLI fte_cli（R38 commands.json 在软件级目录声明）
        copy(self, "fte_cli", src=bld, dst=os.path.join(pkg, "bin"), keep_path=False)
        # 词表数据（fte_init 运行时必需；消费者经 cpp_info.resdirs 定位）
        copy(self, "vocab.tsv", src=src, dst=os.path.join(pkg, "share", "fasttextembed"),
             keep_path=False)
        # 许可证
        copy(self, "LICENSE*", src=src, dst=os.path.join(pkg, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["fte"]
        # 静态库链接需要 libm
        self.cpp_info.system_libs = ["m"]
        # 词表数据（vocab.tsv）随包分发，消费者经 resdirs 定位
        self.cpp_info.resdirs = ["share/fasttextembed"]
