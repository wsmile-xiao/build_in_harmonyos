#!/usr/bin/env python3
"""Conan recipe — passwdqc 2.1.0 (Makefile-based C library).

passwdqc 是密码/密码短语强度检查和策略执行工具集：
- libpasswdqc.so.1：核心检查库（零外部依赖）
- pwqgen/pwqcheck/pwqfilter：命令行工具
- pam_passwdqc.so：PAM 模块（OHOS 无 PAM，跳过构建）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class PasswdqcConan(ConanFile):
    name = "passwdqc"
    version = "2.1.0"
    description = "passwdqc — password/passphrase strength checking and policy enforcement toolset"
    license = "BSD-3-Clause"
    homepage = "https://www.openwall.com/passwdqc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: 编译器必须来自 Conan conf（CI worker 上 ${CC} 等 shell 变量为空）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c", "clang")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cc = self._cc()
        njobs = 1  # R9: 避免 jobserver FIFO 限制，不用 -j$(nproc)
        # OHOS 无 PAM 框架：跳过 pam_passwdqc.so，
        # 仅构建 libpasswdqc.so.1 + pwqgen/pwqcheck/pwqfilter
        # 注意：不能用 all_wrapped（它依赖 pam_wrapped，会编译 pam_passwdqc.c 需要 PAM 头），
        # 改为 utils_wrapped + 单独生成 pkgconfig
        self.run(
            f"make -j{njobs} CC={cc} LD={cc} "
            f"LDFLAGS=-Wl,-soname,libpasswdqc.so.1 utils_wrapped",
            cwd=src,
        )
        # 生成 passwdqc.pc（上游通过 sed 从 .pc.in 生成，make pkgconfig 目标依赖 all）
        self.run(
            f"sed -e 's|@VERSION@|2.1.0|g' passwdqc.pc.in > passwdqc.pc",
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # bin/
        bin_dst = os.path.join(pkg, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        for name in ("pwqgen", "pwqcheck", "pwqfilter"):
            copy(self, name, src=src, dst=bin_dst)

        # lib/
        lib_dst = os.path.join(pkg, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        copy(self, "libpasswdqc.so*", src=src, dst=lib_dst)

        # include/
        inc_dst = os.path.join(pkg, "include")
        os.makedirs(inc_dst, exist_ok=True)
        copy(self, "passwdqc.h", src=src, dst=inc_dst)

        # pkgconfig
        pkgconfig_dst = os.path.join(pkg, "lib", "pkgconfig")
        os.makedirs(pkgconfig_dst, exist_ok=True)
        copy(self, "passwdqc.pc", src=src, dst=pkgconfig_dst)

        # conf
        conf_dst = os.path.join(pkg, "etc")
        os.makedirs(conf_dst, exist_ok=True)
        copy(self, "passwdqc.conf", src=src, dst=conf_dst)

        # man
        man_dst = os.path.join(pkg, "share", "man")
        os.makedirs(man_dst, exist_ok=True)
        for name in ("pwqgen.1", "pwqcheck.1", "pwqfilter.1"):
            copy(self, name, src=src, dst=os.path.join(man_dst, "man1"))
        copy(self, "*.3", src=src, dst=os.path.join(man_dst, "man3"))
        copy(self, "*.5", src=src, dst=os.path.join(man_dst, "man5"))

        # LICENSE
        copy(self, "LICENSE", src=src, dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["passwdqc"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "passwdqc")
        self.cpp_info.set_property("cmake_file_name", "passwdqc")
        self.cpp_info.set_property("cmake_target_name", "passwdqc::passwdqc")
