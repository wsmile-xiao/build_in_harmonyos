#!/usr/bin/env python3
"""Conan recipe — dhcp-helper 1.2 (Makefile).

dhcp-helper is a small DHCP relay agent by the dnsmasq author: one C
translation unit, a bare Makefile (no configure, no test target), and a
version string normally injected through ./get-version. In the release
tarball that script falls back to "UNKNOWN" because the $Format:%d$
placeholder is never substituted, so build() overrides the Makefile's
`version` variable with the real upstream release (command-line make
assignments win over file definitions) and `-v` reports
"dhcp-helper version 1.2".

OHOS notes:
  - libc (musl) already contains the resolver and socket routines, so
    nothing beyond the default LDLIBS is linked.
  - No source patch is needed: the code is plain POSIX C and compiles
    with one upstream -Wsign-compare warning (CMSG_NXTHDR loop).
  - The daemon binds UDP port 67 (or 1067 with -p) and needs root to
    relay, so the consumer test drives only the privilege-free argument
    paths (-v / usage / bad interface / missing server) of the installed
    binary and asserts their exit codes and messages.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DhcpHelperConan(ConanFile):
    name = "dhcp-helper"
    version = "1.2"
    description = "DHCP relay agent forwarding requests between broadcast segments and DHCP servers"
    license = "GPL-2.0-or-later"
    homepage = "https://www.thekelleys.org.uk/dhcp-helper/"
    url = "https://www.thekelleys.org.uk/dhcp-helper/"
    topics = ("dhcp", "relay", "network", "daemon")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dhcp-helper depends on libc only — no third-party dependencies.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dhcp-helper supports Linux/OHOS only, got {self.settings.os}"
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
        # `version=1.2` overrides the Makefile's `$(shell ./get-version)`,
        # which yields UNKNOWN in the release tarball; -fPIE/-pie/relro/now
        # harden the binary. The Makefile appends $(RPM_OPT_FLAGS), empty
        # here, so the flags below are authoritative.
        cflags = "-O2 -fPIE"
        ldflags = "-pie -Wl,-z,relro,-z,now"
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" version="1.2" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        # Upstream installs into PREFIX/sbin; keep that layout.
        copy(self, "dhcp-helper", self.source_folder, os.path.join(self.package_folder, "sbin"))
        os.chmod(os.path.join(self.package_folder, "sbin", "dhcp-helper"), 0o755)
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))
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
        # `env -u LD_LIBRARY_PATH`.
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "sbin", "*"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = []  # dhcp-helper is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["sbin"]
