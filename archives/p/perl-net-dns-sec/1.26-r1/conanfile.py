#!/usr/bin/env python3
"""Conan recipe for perl-net-dns-sec — Perl XS module (Makefile.PL + XS).

Build system: perl Makefile.PL + make + make install
XS module: SEC.xs → SEC.c → SEC.so (links against libcrypto)
Dependencies: OpenSSL (libcrypto), Net::DNS (Perl module)
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlnetdnssecConan(ConanFile):
    name = "perl-net-dns-sec"
    version = "1.26-r1"
    description = "DNSSEC extensions to Net::DNS (Perl XS module with libcrypto)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-DNS-SEC"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenSSL (libcrypto) is installed system-wide; Makefile.PL finds it via pkg-config
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply conandata patches (if any)
        apply_conandata_patches(self)

        # Step 0: Remove any previously installed version to prevent
        # Makefile.PL's custom install() from detecting occlusion
        site_arch = "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux"
        import shutil
        for path in [
            os.path.join(site_arch, "Net", "DNS", "SEC.pm"),
            os.path.join(site_arch, "Net", "DNS", "SEC"),
            os.path.join(site_arch, "auto", "Net", "DNS", "SEC"),
        ]:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)

        # Step 1: Generate Makefile via Makefile.PL
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Patch Makefile for OpenHarmony platform
        #   a) Add sysroot include path for system headers (sys/types.h etc.)
        #   b) Add CRT workaround: -nostartfiles -nodefaultlibs -lc
        makefile_path = os.path.join(self.source_folder, "Makefile")
        with open(makefile_path, "r") as f:
            content = f.read()

        sysroot_inc = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include"
        content = re.sub(
            r"^(CCFLAGS = -D_GNU_SOURCE)",
            rf"CCFLAGS = -isystem {sysroot_inc} -D_GNU_SOURCE",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^LDDLFLAGS = -shared -O2 -fstack-protector-strong$",
            "LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc -O2 -fstack-protector-strong",
            content,
            flags=re.MULTILINE,
        )

        with open(makefile_path, "w") as f:
            f.write(content)

        # Step 3: Build
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install with DESTDIR to package folder
        dest = os.path.join(self.package_folder, "")
        self.run(f"make install DESTDIR={dest}", cwd=self.source_folder)

        # Also copy .so to standard lib/ for package integrity checks
        import shutil
        site_arch_src = os.path.join(
            dest, "data", "service", "hnp", "perl.org",
            "perl_5.42.0", "lib", "site_perl", "5.42.0", "aarch64-linux"
        )
        so_src = os.path.join(site_arch_src, "auto", "Net", "DNS", "SEC", "SEC.so")
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        if os.path.isfile(so_src):
            shutil.copy2(so_src, os.path.join(lib_dst, "SEC.so"))

    def package_info(self):
        # Perl XS module — provides SEC.so (shared library) + Perl .pm files
        # The .so links against libcrypto; libs list for dependency tracking
        self.cpp_info.libs = ["SEC"]
        self.cpp_info.libdirs = ["lib"]
