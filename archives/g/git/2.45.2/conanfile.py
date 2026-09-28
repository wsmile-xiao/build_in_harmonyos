#!/usr/bin/env python3
"""Conan recipe — git 2.45.2 (OHOS aarch64, autotools).

CLI application (R38: commands.json declared at software level).
All adaptation is via official build switches in config.mak; no source
patches, no platform macros. See notes.md for root causes of each switch.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save, chmod
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class GitConan(ConanFile):
    name = "git"
    version = "2.45.2"
    description = "Distributed version control system"
    license = "GPL-2.0-or-later"
    homepage = "https://git-scm.com/"
    url = "https://git-scm.com/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 版本随 curl/8.15.0.1 的依赖锁定关系（见 notes.md「依赖版本」节）
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/3.5.6.1")
        self.requires("curl/8.15.0.1")
        self.requires("expat/2.8.4")

    def layout(self):
        basic_layout(self)
        # git 的 Makefile 是静态的（无 VPATH 支持），configure 生成的
        # config.mak.autogen 必须与 Makefile 同目录 → in-source 构建
        self.folders.build = self.folders.source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure 的 conftest 运行期需要加载依赖 .so（libexpat.so 等），
        # 把依赖 libdir 注入 LD_LIBRARY_PATH，否则报 "Error loading shared
        # library libexpat.so" → "cannot run C compiled programs"（知识 E540 同族）
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                self.buildenv.prepend_path("LD_LIBRARY_PATH",
                                           os.path.join(dep.package_folder, libdir))
        tc = AutotoolsToolchain(self)
        tc.configure_args += [
            "--with-openssl",
            "--with-curl",
            "--with-expat",
            # bionic 无 libintl.so：SDK sysroot 自带 libintl.h 会诱导 configure
            # 向 LIBS 追加 -lintl，污染后续所有链接型探测（notes.md 问题#1）
            "ac_cv_header_libintl_h=no",
        ]
        tc.generate()
        # 注入依赖的 -I/-L/-l（zlib/openssl/curl/expat），否则 configure
        # 探测不到 curl_global_init/CRYPTO_new_ex_data → NO_CURL/NO_OPENSSL
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        # git Makefile 的权威覆盖点：-include config.mak 位于
        # config.mak.uname / config.mak.autogen 之后，最后赋值生效。
        # 全部为官方构建开关（R33：不依赖 shell 环境变量）
        save(self, os.path.join(self.source_folder, "config.mak"), CONFIG_MAK)
        apply_conandata_patches(self)
        # E490: 补丁应用可能丢失 autotools 脚本执行位，恢复
        chmod(self, os.path.join(self.source_folder, "configure"), 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMDFS UID 映射触发 safe.directory dubious ownership（历史归档坑，
        # archives/g/git/README.md）：包内系统级 gitconfig 放行
        save(self, os.path.join(self.package_folder, "etc", "gitconfig"),
             "[safe]\n\tdirectory = *\n")

    def package_info(self):
        # CLI 应用：无头文件/无库；产物为 bin/git 与 libexec/git-core/*
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]


CONFIG_MAK = """\
HAVE_DEV_TTY=YesPlease
NO_PERL=YesPlease
NO_TCLTK=YesPlease
NO_PTHREADS=YesPlease
CURL_LDFLAGS=-lcurl
# OHOS 无独立 install(1)，/system/bin 提供 busybox applet
INSTALL=/system/bin/install
RUNTIME_PREFIX=YesPlease
"""
