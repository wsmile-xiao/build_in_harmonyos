#!/usr/bin/env python3
"""Conan recipe for mpssh 1.3.3 — mass parallel SSH tool.

mpssh spawns parallel ssh processes to run a command on many hosts at
once, reading the target list from a hosts file (user@host:port per line,
%label groups supported).

Build: plain Makefile (no configure, no make install usable on OHOS —
its install target hardcodes GNU coreutils `install` and /usr/local/bin).
Deps: none (only libc; it execs the external ssh/scp binaries).

See: https://github.com/ndenev/mpssh
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MpsshConan(ConanFile):
    name = "mpssh"
    version = "1.3.3"
    description = "Mass parallel ssh — run a command on many hosts at once"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ndenev/mpssh"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never from shell env.
        # Makefile hardcodes CC = gcc / LD = gcc; OHOS toolchain is clang,
        # so both must be overridden explicitly.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # Makefile bakes SSHPATH/SCPPATH into the binary at compile time via
        # -DSSHPATH=... (execv uses these absolute paths at runtime). Bake
        # the standard OHOS locations so the binary is self-contained.
        # R9: always -j1 (tiny build anyway).
        self.run(
            f"make -C {self.source_folder} CC={cc} LD={cc} "
            f"SSHPATH=/usr/bin/ssh SCPPATH=/usr/bin/scp "
            f"-j1"
        )

    def package(self):
        # Single binary + man page (make install unusable: GNU install + /usr/local/bin)
        copy(self, "mpssh", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mpssh.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # R38/E082: HarmonyOS requires ELF signing before a binary can execute.
        bin_path = os.path.join(self.package_folder, "bin", "mpssh")
        if os.path.exists(bin_path) and self.settings.os in ("Linux", "OHOS"):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            if os.path.exists(sign_tool):
                tmp_signed = bin_path + ".signed"
                # .codesign section may not exist on a fresh build — tolerate failure
                self.run(f"{objcopy} --remove-section .codesign {bin_path} || true", quiet=True)
                self.run(f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} "
                         f"-selfSign 1", quiet=True)
                os.replace(tmp_signed, bin_path)
                os.chmod(bin_path, 0o755)

    def package_info(self):
        # Application — single binary, no libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
