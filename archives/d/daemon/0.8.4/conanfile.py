#!/usr/bin/env python3
"""Conan recipe for daemon 0.8.4 — raf's daemon tool (https://libslack.org/daemon).

*daemon* turns other processes into daemons (setsid, pidfile, respawn, signals,
pty, syslog redirection, etc.). It is a C command-line tool that links against
the vendored libslack static library.

Build system: raf's custom Makefile + ./configure platform detection
(not autotools, not cmake). License: GPL-2.0-or-later.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DaemonConan(ConanFile):
    name = "daemon"
    version = "0.8.4"
    description = "Turns other processes into daemons (raf's daemon tool)"
    license = "GPL-2.0-or-later"
    homepage = "https://libslack.org/daemon"
    url = ""  # filled by CI
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # raf's build is in-source (configure rewrites Makefile/macros.mk/config.h),
        # so build and source share the same directory.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def requirements(self):
        pass  # No external Conan deps: libslack is vendored; pthread/util from musl

    def source(self):
        # Download and extract the upstream tarball declared in conandata.yml.
        # This was previously missing — without it source_folder is empty and
        # build()'s ./configure fails with "No such file or directory".
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take toolchain paths from Conan conf, never from shell env.
        # The profile registers tools.build:compiler_executables as a *dict*
        # ({c, cpp}); the `:c`/`:ar` sub-key form is NOT a registered conf and
        # raises ConanException, so read the dict and index it. The raf Makefile
        # assigns CC/AR/RANLIB with `:=` (ignoring the environment), so they must
        # be passed on the `make` command line (command line overrides `:=`).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "/data/service/hnp/bin/llvm-ar")
        ranlib = compilers.get("ranlib", "/data/service/hnp/bin/llvm-ranlib")
        # GNU ld avoids the OHOS SDK lld -> libxml2.so.16 link failure (E120/E132).
        ld = "/data/service/hnp/bin/ld"

        # raf builds in-source (configure rewrites Makefile/macros.mk/config.h in
        # the source tree), and conan create keeps source_folder and build_folder
        # in separate directories. So run configure/make in source_folder (where
        # configure actually lives), matching the verified pmccabe pattern.
        sh = os.environ.get("CONFIG_SHELL", "sh")
        self.run(f'"{sh}" ./configure --platform=Linux --disable-logind --disable-mail-test',
                 cwd=self.source_folder)
        self.run(
            'make -j1 '
            'CC="{cc}" AR="{ar}" RANLIB="{ranlib}" '
            'LDFLAGS="-fuse-ld={ld}"'.format(cc=cc, ar=ar, ranlib=ranlib, ld=ld),
            cwd=self.source_folder)

    def package(self):
        # Copy the daemon executable only (built in source_folder, see build()).
        # `make install` is avoided because it also requires pod2man (man pages)
        # and runs strip; neither is needed here.
        copy(self, "daemon", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # HarmonyOS requires ELF signing before a binary can be executed (E082);
        # without this the test_package cannot run the daemon binary.
        bin_path = os.path.join(self.package_folder, "bin", "daemon")
        if os.path.exists(bin_path):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {bin_path}", quiet=True)
            self.run(f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} "
                     f"-selfSign 1", quiet=True)
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        # Tool-only package: ships an executable, no libraries to link against.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
