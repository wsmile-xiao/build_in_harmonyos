#!/usr/bin/env python3
"""Conan recipe — irpas 0.10 (Makefile project, CLI tools).

irpas: Internetwork Routing Protocol Attack Suite (Phenoelit).
Build: plain Makefile producing 16 CLI binaries; bundled libpcap-0.4 is
       NOT built (sys_nerr/sys_errlist absent on OHOS musl); use registry
       libpcap/1.10.6 + libtirpc/1.3.7 instead (R18 prebuilt preference).
License: Phenoelit-License (see http://www.phenoelit.de/fr/license.html)
"""
import hashlib
import os
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# 16 CLI programs produced by the upstream Makefile (TARGETS)
IRPAS_PROGRAMS = [
    "cdp", "igrp", "ass", "irdp", "irdpresponder", "itrace", "tctrace",
    "protos", "netmask", "file2cable", "dfkaa", "netenum", "hsrp",
    "icmp_redirect", "timestamp", "dhcpx",
]


class IrpasConan(ConanFile):
    name = "irpas"
    version = "0.10"
    description = "Internetwork Routing Protocol Attack Suite - 网络路由协议测试/审计工具集"
    license = "Phenoelit-License"
    homepage = "http://www.phenoelit.de/irpas/"
    url = "https://www.phenoelit.de/irpas/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime deps of the tool suite (raw sockets + RPC)
        self.requires("libpcap/1.10.6")
        self.requires("libtirpc/1.3.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        # phenoelit.de serves the .tar.gz with `Content-Encoding: gzip`, which
        # makes conan's requests-based get() auto-decompress the transfer and
        # hash-check the DECOMPRESSED bytes (hash mismatch vs conandata.yml).
        # Use urllib (no auto-decompress) + explicit sha256 verify + tarfile extract.
        url = self.conan_data["sources"]["url"]
        expected = self.conan_data["sources"]["sha256"]
        fname = self.conan_data["sources"].get("filename", url.rsplit("/", 1)[-1])
        dest = os.path.join(self.source_folder, fname)
        req = urllib.request.Request(url, headers={"User-Agent": "Conan/2.x (irpas recipe)"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ConanException(
                f"sha256 mismatch for {fname}: got {actual}, expected {expected}"
            )
        with open(dest, "wb") as f:
            f.write(data)
        with tarfile.open(dest) as tf:
            tf.extractall(self.source_folder)
        os.unlink(dest)

    def generate(self):
        # R49: dependency injection via build-folder private prefix.
        # Works for both root CppInfo and componentized deps (_Component):
        # includedirs/libdirs are package-folder-relative; join to absolute.
        incs = []
        libs = []
        for dep in self.dependencies.values():
            pkg = str(dep.package_folder)
            cpp = dep.cpp_info
            comps = getattr(cpp, "components", None) or {}
            targets = list(comps.values()) if comps else [cpp]
            for t in targets:
                for d in getattr(t, "includedirs", None) or []:
                    incs.append(os.path.join(pkg, d))
                for d in getattr(t, "libdirs", None) or []:
                    libs.append(os.path.join(pkg, d))
        inc_flags = " ".join(f"-I{p}" for p in incs)
        lib_flags = " ".join(f"-L{p}" for p in libs)
        # record flags for build()
        self._ohos_inc_flags = inc_flags
        self._ohos_lib_flags = lib_flags

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf (never shell env vars).
        # Some conan builds reject sub-key access "tools.build:compiler_executables:c";
        # read the whole dict and index instead.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        # -I./libpcap-0.4 provides net/bpf.h (source-tree header only; the bundled
        # libpcap-0.4 is NOT built — use registry libpcap/1.10.6 instead)
        cflags = (
            "-Wall -g -Wunused -Wmissing-prototypes -I. -L. -I./libpcap-0.4 "
            + self._ohos_inc_flags + " " + self._ohos_lib_flags
        )
        # R9: -j1; build the 16 program targets only (avoids bundled libpcap build).
        # basic_layout puts build() cwd in build-release/; Makefile lives at the
        # copied-source root (self.source_folder), so cd there first.
        targets = " ".join(IRPAS_PROGRAMS)
        self.run(
            f'cd {self.source_folder} && make CC={cc} CFLAGS="{cflags}" '
            f'CLIBS="-lpcap -ltirpc" {targets} -j1'
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for prog in IRPAS_PROGRAMS:
            src = os.path.join(self.source_folder, prog)
            if os.path.exists(src):
                copy(self, prog, self.source_folder, bin_dir)

    def package_info(self):
        # CLI tools only: expose bin dir
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = []

    def package_id(self):
        # tools are arch-agnostic in behavior but built per-arch; keep default
        pass