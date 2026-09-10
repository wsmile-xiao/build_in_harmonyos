#!/usr/bin/env python3
"""Conan recipe — connect-proxy 1.105 (Makefile).

connect-proxy (upstream ssh-connect) is a single-file C program used as an ssh
ProxyCommand to relay TCP connections through SOCKS4/SOCKS5 or HTTP CONNECT
proxies. Debian/Termux distribute the same program under the connect-proxy
name, and so does this archive; package() installs the binary as
bin/connect-proxy.

Upstream ships a bare Makefile with no configure and no install target, and it
hardcodes CC=gcc, so build() overrides CC/CFLAGS/LDFLAGS with values taken from
the Conan toolchain (R33) and package() installs the binary by hand.

OHOS notes:
  - libc (musl) already contains the resolver and socket routines, so the
    -lresolv / -lsocket / -lnsl of other platforms must not be linked.
  - The upstream Makefile only special-cases Darwin/SunOS/Windows; OHOS falls
    into the generic UNIX branch, so the build itself needs no patch.
  - patches/0001-connect.c.patch ports switch_ns() ('-R <nameserver-ip>'):
    musl has no glibc _res resolver state, so the nameserver is queried over
    UDP directly. The musl guard is __linux__ && !__GLIBC__ (equivalent on
    OHOS; keeps the patch free of platform macros, R8).
  - patches/0002-connect.c.patch keeps connect usable when /etc/passwd has no
    entry for the current uid (normal on OHOS).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ConnectProxyConan(ConanFile):
    name = "connect-proxy"
    version = "1.105"
    description = "Relay command to make socket connections via SOCKS4/5 and HTTP tunnel (ssh ProxyCommand)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/gotoh/ssh-connect"
    url = "https://github.com/gotoh/ssh-connect"
    topics = ("socks", "socks5", "http-proxy", "ssh", "proxycommand", "tunnel")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # connect-proxy depends on libc only — no third-party dependencies.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"connect-proxy supports Linux/OHOS only, got {self.settings.os}"
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

    def generate(self):
        # Record the resolved compiler in the build env for traceability.
        env = Environment()
        env.define("CC", self._compiler_c())
        env.vars(self).save_script("conanbuild_cc")

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_c()
        # -DSOCKLEN_T=socklen_t mirrors upstream's Makefile define with the type
        # that is correct on OHOS; -fPIE/-pie/relro/now harden the binary.
        cflags = "-O2 -fPIE -D_GNU_SOURCE -DSOCKLEN_T=socklen_t"
        ldflags = "-pie -Wl,-z,relro,-z,now"
        # LDLIBS is emptied on purpose: musl bundles the resolver into libc.
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" LDLIBS="" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        # Install as connect-proxy (Debian/Termux naming) so the binary name
        # matches the package and does not collide with other connect tools.
        copy(self, "connect", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Upstream ships no LICENSE file; the GPL-2.0-or-later notice lives in
        # the connect.c header and the README.
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        os.chmod(os.path.join(self.package_folder, "bin", "connect"), 0o755)
        os.rename(
            os.path.join(self.package_folder, "bin", "connect"),
            os.path.join(self.package_folder, "bin", "connect-proxy"),
        )
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires signed executables; sign the installed binary
        # in place. The hnp tools resolve libc++ via their own location, so the
        # environment must not carry an LD_LIBRARY_PATH pointing at SDK/llvm
        # libs (the ohos-aarch64 profile buildenv prepends them) — hence
        # `env -u LD_LIBRARY_PATH` (a conflicting libc++.so otherwise makes
        # binary-sign-tool fail with "Error relocating ... symbol not found").
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
        self.cpp_info.libs = []  # connect-proxy is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
