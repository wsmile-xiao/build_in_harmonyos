#!/usr/bin/env python3
"""Conan recipe — ubench 0.32 (Unix Benchmark Utility, Sergei Viznyuk, 1999-2000).

Build system: upstream ships a hand-written ``configure`` that only writes a
Makefile from ``uname`` (host ``uname -m`` picks ``gcc -m486 -malign-*``), and
the Makefile runs the host ``strip`` on the result.  Neither is usable for a
cross build, so ``build()`` compiles the exact object list of the upstream
``ubench`` target (signals, cpubench, membench, ubench) with the Conan
compiler.  ``diskbench.c``/``netbench.c`` (only built with -DDISKNETYES) and
the separate ``utime`` helper are not part of the upstream default target.

Patches (portable, no platform macros):
  * ``sys_errlist[errno]`` -> ``strerror(errno)`` (musl never exported the
    array; glibc removed it in 2.32);
  * ``CLK_TCK`` -> ``sysconf(_SC_CLK_TCK)`` (obsolete macro, absent from
    musl/POSIX.1-2001 headers);
  * cpubench.c: include ``<stdlib.h>``/``<string.h>`` for exit/abs/strerror.

Linking: ``-static-pie``.  ubench only needs libc + libm; a static PIE keeps
PIE/RELRO, removes the runtime dependency on /lib/ld-musl-aarch64.so.1 and
lets the same artefact run on the OHOS device and under qemu-aarch64.
"""
import os
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, check_sha256, copy,
                               export_conandata_patches, get, unzip)
from conan.tools.layout import basic_layout


class UbenchConan(ConanFile):
    name = "ubench"
    version = "0.32"
    description = "ubench - Unix Benchmark Utility (CPU and memory benchmark)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.ibiblio.org/pub/Linux/system/benchmark/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("benchmark", "cpu", "memory", "cli")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _objects = ("signals", "cpubench", "membench", "ubench")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ubench 0.32 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]
        try:
            get(self, **data, strip_root=True)
            return
        except ConanException as exc:
            # www.ibiblio.org answers .tar.gz with "Content-Encoding: gzip" /
            # "x-gzip"; Conan's requests/urllib3 decodes one layer and hashes
            # the inner plain tar (c21b18a5...), not the published file
            # (92277fe3..., curl -O).  urllib keeps the raw bytes, so the
            # canonical sha256 is still enforced (simstring 1.0 precedent).
            self.output.warning(f"conan downloader failed ({exc}); retrying with urllib "
                                "(server sends Content-Encoding: x-gzip for .tar.gz)")
        archive = os.path.join(self.source_folder, "ubench-0.32.tar.gz")
        with urllib.request.urlopen(data["url"], timeout=120) as resp:
            payload = resp.read()
        with open(archive, "wb") as handle:
            handle.write(payload)
        check_sha256(self, archive, data["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = compilers.get("c", "cc")
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        cflags = f"{opt} -fPIE -Wall -Wno-deprecated-non-prototype -I."
        for obj in self._objects:
            self.run(f"'{cc}' {cflags} -c {obj}.c -o {obj}.o",
                     env="conanbuild", cwd=self.source_folder)
        objs = " ".join(f"{obj}.o" for obj in self._objects)
        # upstream LDFLAGS "-s -lm"; -lm moved after the objects
        self.run(f"'{cc}' {opt} -static-pie -s -o ubench {objs} -lm",
                 env="conanbuild", cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "ubench", src=self.source_folder, dst=bindir)
        os.chmod(os.path.join(bindir, "ubench"), 0o755)
        copy(self, "ubench.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
