#!/usr/bin/env python3
"""Conan recipe — cisco7crack 0.0-git20121221.f1c21dd (no build system).

A single-file C program (cisco7crack.c) that crypts and decrypts Cisco IOS
type-7 passwords. The upstream git snapshot ships no build system at all; the
reference command in the source header is

    gcc -Wall -W -ansi -pedantic -O2 cisco7crack.c -o cisco7crack

build() mirrors that with the compiler taken from the Conan profile (R33) and
adds PIE/RELRO hardening; package() installs the binary by hand and signs it
for the HarmonyOS XPM loader.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Cisco7CrackConan(ConanFile):
    name = "cisco7crack"
    version = "0.0-git20121221.f1c21dd"
    description = "Crypt and decrypt Cisco IOS type-7 (enable) passwords"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/madrisan/cisco7crack"
    url = "https://github.com/madrisan/cisco7crack"
    topics = ("cisco", "ios", "type-7", "password", "security")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libc only — no third-party dependencies.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cisco7crack supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_c()
        # 上游无构建系统；对齐源码头注释的参考命令（-Wall -W -O2），
        # 去掉 -ansi/-pedantic（clang15 对该 2002 年代码的告警不构成错误），
        # 追加 -D_GNU_SOURCE（OHOS/musl 头文件兼容）与 PIE/RELRO 加固。
        cflags = "-O2 -fPIE -D_GNU_SOURCE -Wall -W"
        ldflags = "-pie -Wl,-z,relro,-z,now"
        self.run(
            f"{cc} {cflags} cisco7crack.c -o cisco7crack {ldflags}",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "cisco7crack", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        # 上游没有独立的 LICENSE 文件，GPL-2.0-or-later 声明在 cisco7crack.c
        # 头注释与 README.md 中，随 licenses/ 一起安装。
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        os.chmod(os.path.join(self.package_folder, "bin", "cisco7crack"), 0o755)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM 要求被 exec 的 ELF 自签；签名必须发生在链接之后且
        # 之后不再改动文件内容。hnp 工具链自带 libc++ 解析依赖自身所在路径，
        # profile buildenv 前置的 SDK llvm/lib LD_LIBRARY_PATH 会遮蔽它
        # （报 "Error relocating ... symbol not found"），故用 env -u 清除。
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "bin", "*"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = []  # cisco7crack is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
