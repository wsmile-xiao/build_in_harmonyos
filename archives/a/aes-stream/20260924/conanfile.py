#!/usr/bin/env python3
"""Conan recipe for aes-stream 20260924.

上游 aes-stream 无任何构建系统（纯 src/aes-stream.c + src/aes-stream.h），
且源码仅含 x86 AES-NI intrinsics（immintrin.h / __m128i），无法在 OHOS arm64
目标上编译。本配方携带 ARMv8 crypto extension 移植实现
src/aes-stream-arm.c（逐位镜像上游构造，已与标量参考 bit-exact 对拍验证），
在 OHOS（aarch64）上直接编译该实现，产出同名静态库 libaes_stream.a 与官方头
aes-stream.h。

R38：纯库类型（无 bin 产物），不需要 commands.json。
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

ARM_MARCH = "-march=armv8-a+crypto"  # ARMv8 crypto extension（AESE/AESMC）


class AesstreamConan(ConanFile):
    name = "aes-stream"
    version = "20260924"
    description = "A fast AES-PRF based secure random-number generator"
    license = "BSD-2-Clause"
    homepage = "https://github.com/jedisct1/aes-stream"
    url = "https://github.com/jedisct1/aes-stream"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*", "src/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aes-stream supports Linux/OHOS in this recipe, got {self.settings.os}"
            )
        if self.settings.arch == "x86_64" or "x86" in str(self.settings.arch):
            raise ConanInvalidConfiguration(
                "aes-stream upstream source is x86 AES-NI only; this recipe ships "
                "the ARMv8 crypto port and targets aarch64 OHOS"
            )

    def source(self):
        source = dict(self.conan_data["sources"])
        source["filename"] = "aes-stream-20260924.tar.gz"
        get(self, **source, strip_root=True, verify=True)

    def build(self):
        apply_conandata_patches(self)  # 空补丁时无害，G1 要求
        # 官方头（可移植）随源码下载；ARM 实现由配方携带（exports_sources src/*）
        cc = self._resolve_compiler()
        cflags = self._cflags()
        src_dir = os.path.join(self.source_folder, "src")
        impl = os.path.join(src_dir, "aes-stream-arm.c")
        if not os.path.exists(impl):
            raise RuntimeError("aes-stream-arm.c not found in source tree; "
                               "expected it via exports_sources from the recipe src/")
        obj = os.path.join(self.build_folder, "aes-stream-arm.o")
        cmd = [cc, "-c"] + cflags + [ARM_MARCH,
                                     "-I" + src_dir, impl, "-o", obj]
        self.run(" ".join(shlex.quote(t) for t in cmd),
                 cwd=self.build_folder)
        ar = self._resolve_tool(
            (self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}).get("ar"), "llvm-ar")
        static_lib = os.path.join(self.build_folder, "libaes_stream.a")
        self.run(
            "{} rcs {} {}".format(shlex.quote(ar), shlex.quote(static_lib),
                                  shlex.quote(obj)),
            cwd=self.build_folder,
        )
        if self.options.shared:
            ld = self._resolve_tool(
                (self.conf.get("tools.build:compiler_executables", default={},
                               check_type=dict) or {}).get("cxx"), "clang++")
            shared_lib = os.path.join(self.build_folder, "libaes_stream.so")
            self.run(
                "{} -shared -fPIC -o {} {}".format(
                    shlex.quote(ld), shlex.quote(shared_lib), shlex.quote(obj)),
                cwd=self.build_folder,
            )

    def package(self):
        copy(self, "aes-stream.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for lib in ("libaes_stream.a", "libaes_stream.so"):
            for base in (self.build_folder,):
                p = os.path.join(base, lib)
                if os.path.exists(p):
                    copy(self, lib, src=base,
                         dst=os.path.join(self.package_folder, "lib"),
                         keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["aes_stream"]

    # ---- helpers ----
    def _resolve_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return self._resolve_tool(compilers.get("c") or compilers.get("cc"), "clang")

    def _resolve_tool(self, tool, fallback):
        if tool:
            return str(tool)
        for candidate in (fallback, "clang", "llvm-ar", "clang++"):
            return candidate
        return fallback

    def _cflags(self):
        flags = ["-O2", "-fPIC"]
        if self.settings.build_type == "Debug":
            flags = ["-O0", "-g", "-fPIC"]
        lflags = self.conf.get("tools.build:cflags", default=[], check_type=list)
        return flags + list(lflags)