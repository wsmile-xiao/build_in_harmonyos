#!/usr/bin/env python3
"""Conan recipe for mini_httpd — small HTTP server from ACME Labs.

mini_httpd is a command-line tool (application), not a library.
Build outputs: mini_httpd (HTTP server) and htpasswd (password tool).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MiniHttpdConan(ConanFile):
    name = "mini_httpd"
    version = "1.30"
    description = "Small, lightweight HTTP server from ACME Labs"
    license = "BSD-like"
    homepage = "https://www.acme.com/software/mini_httpd/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # mini_httpd has no configure script — just a raw Makefile.
        # Detect getpass() via try-compile; pass -DNO_GETPASS if missing
        # so the replacement implementation in the patch is activated.
        cflags = "-O2 -Wall"
        if not self._check_getpass():
            cflags += " -DNO_GETPASS"
        # R9: Always use -j1. Run in source folder where Makefile lives.
        # Pass CC="${CC:-cc}" so make uses the same compiler as _check_getpass()
        # (Conan build env's cross-compiler in cross-build scenarios).
        self.run(f'make -j1 CC="${{CC:-cc}}" CFLAGS="{cflags}"', cwd=self.source_folder)

    def _check_getpass(self):
        """Check if getpass() is available by linking a small test program.

        mini_httpd's Makefile has no configure step, so we do a minimal
        try-link to detect whether <unistd.h> provides getpass() AND the
        C library actually provides the symbol.

        Note: must use full link (not -c compile-only), because getpass()
        may be declared in <unistd.h> (compiles fine via implicit declaration)
        but not implemented in the C library (e.g. OHOS libc), which only
        surfaces at link time as "undefined symbol: getpass".

        Uses ${CC:-cc} so the Conan build environment's cross-compiler
        (e.g. aarch64-linux-ohos-clang) is used in cross-build scenarios,
        rather than reading os.environ which only has the host CC.
        """
        test_c = os.path.join(self.build_folder, "_getpass_test.c")
        test_out = os.path.join(self.build_folder, "_getpass_test.out")
        with open(test_c, "w") as f:
            f.write('#include <unistd.h>\nint main(void){getpass("x");return 0;}\n')
        try:
            self.run(f'${{CC:-cc}} {test_c} -o {test_out}', cwd=self.build_folder)
            return True
        except Exception:
            return False
        finally:
            for _f in (test_c, test_out):
                if os.path.exists(_f):
                    os.remove(_f)

    def package(self):
        # Install executables via make install, overriding BINDIR/MANDIR
        # to install into the Conan package folder directly.
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man")
        self.run(f"make install BINDIR={bindir} MANDIR={mandir}", cwd=self.source_folder)

    def package_info(self):
        # mini_httpd is an application — expose bindirs for executables
        self.cpp_info.bindirs = ["bin"]
