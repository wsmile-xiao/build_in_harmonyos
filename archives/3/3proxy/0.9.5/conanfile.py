#!/usr/bin/env python3
"""Conan recipe for 3proxy 0.9.5 - raw GNU Makefile family (no ./configure).

Upstream ships a Makefile family (Makefile.Linux/FreeBSD/Solaris/unix/win/msvc/
watcom/llvm/debug ...), there is NO autotools `configure` in the tree. The root
Makefile.Linux copies itself to src/Makefile.var and recurses into src/, where
src/Makefile.inc links the 10 proxy binaries plus the 4 loadable plugins.

OHOS portability note (knowledge entry E119, macro-guard-skip-header): the OHOS
SDK ships both `sys/socket.h` and the kernel uapi `linux/socket.h`, and
linux/netfilter_ipv4.h pulls the latter in -> `redefinition of struct
sockaddr_storage`. The recipe appends the neutral macro `-D_UAPI_LINUX_SOCKET_H`
to upstream's own CFLAGS so the uapi header is skipped. The define is injected
recipe-side as a build flag on purpose: patches must not carry platform macros
(R8 / preflight PF5).
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class P3ProxyConan(ConanFile):
    name = "3proxy"
    version = "0.9.5"
    description = "3proxy - lightweight multi-protocol proxy server (HTTP/SOCKS4/SOCKS5/SMTP/POP3/FTP/TCP/UDP mapper, auth, ACL, logging)"
    license = "3proxy 0.9 Public License"
    homepage = "https://3proxy.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URLs end in the tag name (e.g. ".../tar.gz/refs/tags/0.9.5")
        # which has no file extension, so Conan get() deduces filename "0.9.5"
        # and unzip() falls back to the zip decoder -> BadZipFile. Pass an
        # explicit *.tar.gz filename so unzip() selects the tar.gz decoder.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="3proxy-0.9.5.tar.gz")

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan conf, never from bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"

        # Take upstream's own CFLAGS and append the neutral E119 guard define.
        mkfile = os.path.join(self.source_folder, "Makefile.Linux")
        with open(mkfile, "r", encoding="utf-8") as fh:
            text = fh.read()
        match = re.search(r"^CFLAGS = (.*)$", text, re.M)
        if not match:
            raise Exception("Makefile.Linux: CFLAGS line not found, recipe needs update")
        cflags = match.group(1).strip() + " -D_UAPI_LINUX_SOCKET_H"

        # R9: always -j1. `CFLAGS=` on the command line is inherited by the
        # src/ and plugin sub-makes, so every compilation unit gets the guard.
        self.run(
            'make -f Makefile.Linux CC="{}" CFLAGS="{}" -j1'.format(cc, cflags),
            cwd=self.source_folder,
        )

    def package(self):
        src_bin = os.path.join(self.source_folder, "bin")
        bindir = os.path.join(self.package_folder, "bin")
        libexec = os.path.join(self.package_folder, "libexec", "3proxy")

        for exe in ("3proxy", "proxy", "socks", "smtpp", "pop3p", "ftppr",
                    "tcppm", "tlspr", "udppm", "mycrypt"):
            copy(self, exe, src_bin, bindir)
        for plugin in ("StringsPlugin.ld.so", "TrafficPlugin.ld.so",
                       "PCREPlugin.ld.so", "TransparentPlugin.ld.so"):
            copy(self, plugin, src_bin, libexec)

        man = os.path.join(self.source_folder, "man")
        if os.path.isdir(man):
            for section in ("1", "3", "8"):
                copy(self, "*." + section, man,
                     os.path.join(self.package_folder, "share", "man", "man" + section))
        sample = os.path.join(self.source_folder, "cfg", "3proxy.cfg.sample")
        if os.path.isfile(sample):
            copy(self, "3proxy.cfg.sample",
                 os.path.join(self.source_folder, "cfg"),
                 os.path.join(self.package_folder, "share", "3proxy"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
