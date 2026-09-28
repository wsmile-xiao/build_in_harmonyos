#!/usr/bin/env python3
"""Conan recipe for socat 1.8.1.3 (HarmonyOS PC, aarch64).

socat is an autotools-based CLI application (binaries: socat, filan, procan).
Adaptation notes for OHOS:
  - configure: HMDFS temp dir cannot honour umask 077 (fixed in patch 0001)
  - --disable-resolve: OHOS musl has no global `_res` resolver state
  - sockaddr_storage redefinition guard between linux/socket.h and sys/socket.h
  - filan: isastream() unavailable in musl, guarded by HAVE_ISASTREAM check
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SocatConan(ConanFile):
    name = "socat"
    version = "1.8.1.3"
    description = "Socat — multipurpose relay for bidirectional data transfer"
    license = "GPL-2.0"
    homepage = "http://www.dest-unreach.org/socat/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/4.0.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"OS {self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS musl libc lacks the global `_res` resolver state; disable the
        # undocumented resolver-options feature so xio-ip.c compiles cleanly.
        tc.configure_args.append("--disable-resolve")
        # r03: 启用 OPENSSL 特性（依赖已在 r03 终态复核确认可消费）
        if self.dependencies.get("openssl"):
            pkg = self.dependencies["openssl"].package_folder
            if pkg:
                tc.configure_args.append("--enable-openssl-base=%s" % pkg)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        import os
        import shutil
        autotools = Autotools(self)
        # socat Makefile 的 install 规则引用 SHFILES 时未加 $(srcdir) 前缀，
        # out-of-source 构建下脚本不在 build 目录导致 ginstall 找不到；先复制。
        for f in ("socat-chain.sh", "socat-mux.sh", "socat-broker.sh",
                  "daemon.sh", "mail.sh", "ftp.sh", "readline.sh",
                  "socat_buildscript_for_android.sh"):
            src = os.path.join(self.source_folder, f)
            dst = os.path.join(self.build_folder, f)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
