#!/usr/bin/env python3
"""Conan recipe — tcpkali 1.1.1 (Autotools)

tcpkali is a high-performance TCP/WebSocket load testing tool based on libev.
Core executable: tcpkali (CLI tool for TCP/WebSocket stress testing).

OHOS adaptation notes:
- OHOS musl libc lacks __containerof/QUEUE_TYPEOF macros in sys/queue.h
- OHOS musl libc does not provide sys/sysctl.h
- Source archive has no pre-generated configure; CI workers lack
  automake/aclocal, so pre-generated autotools files (aclocal.m4,
  Makefile.in, config/ aux scripts, m4/ macros) are shipped as text
  files in prebuilt/ and copied into the source tree. Only autoconf
  (available on CI) is run to generate configure.
- ncurses statically linked (system prebuilt), binary only depends on libc.so
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TcpkaliConan(ConanFile):
    name = "tcpkali"
    version = "1.1.1"
    package_type = "application"
    description = "High-performance TCP/WebSocket load testing tool based on libev"
    license = "BSD-2-Clause"
    homepage = "https://github.com/MumiaiGene/tcpkali"
    url = ""

    # R32: settings.os must allow both Linux and OHOS
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # CI workers lack automake/aclocal; ship pre-generated autotools
        # files (aclocal.m4, Makefile.in, config/, m4/) as text files.
        copy(self, "*", src=os.path.join(self.recipe_folder, "prebuilt"),
             dst=self.export_sources_folder)

    def requirements(self):
        # ncurses is available as system prebuilt (like bash recipe).
        # Not declared as conan requires to avoid /lib pollution (R26).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: ncurses is a system library, static link to avoid polluting /lib
        tc.extra_ldflags.append("-static")
        # config.guess may not recognize HarmonyOS; derive build triplet from
        # settings.arch so it works for any target architecture.
        build_arch = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
        tc.configure_args.append(f"--build={build_arch}-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Copy pre-generated autotools files into source tree.
        # These were generated with automake/aclocal/libtoolize locally;
        # CI workers only have autoconf (not automake/aclocal).
        prebuilt_dir = os.path.join(self.source_folder, "prebuilt")
        for root, _, files in os.walk(prebuilt_dir):
            rel = os.path.relpath(root, prebuilt_dir)
            dst = self.source_folder if rel == "." else os.path.join(self.source_folder, rel)
            for f in files:
                src_path = os.path.join(root, f)
                dst_path = os.path.join(dst, f)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
        # Generate configure using autoconf (available on CI workers).
        # aclocal.m4 + m4/ macros are pre-shipped, so autoconf can resolve
        # all macros (AM_INIT_AUTOMAKE, LT_INIT, AX_PTHREAD, etc.).
        self.run("autoconf", cwd=self.source_folder)
        self.run("autoheader", cwd=self.source_folder)
        # Touch generated files to prevent make from re-running aclocal/automake
        self.run("touch aclocal.m4 configure config.h.in "
                 "Makefile.in deps/*/Makefile.in src/Makefile.in test/Makefile.in doc/Makefile.in",
                 cwd=self.source_folder)
        if self.settings.os == "OHOS":
            # Fix shebangs (no /bin/sh on OpenHarmony)
            for f in ["configure", "config/compile", "config/missing",
                       "config/install-sh", "config/config.sub",
                       "config/config.guess", "config/depcomp",
                       "config/test-driver"]:
                path = os.path.join(self.source_folder, f)
                if os.path.exists(path):
                    self.run(f"sed -i '1s|^#!.*|#!/data/service/hnp/bin/bash|' {path}")
            # Remove umask 077 from temp dir creation (HMDFS blocks file
            # creation in 700-permission directories)
            self.run("sed -i 's/umask 077/umask 007/g' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # tcpkali produces an executable, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
