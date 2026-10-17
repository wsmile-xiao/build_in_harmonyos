#!/usr/bin/env python3
"""Conan recipe for perl-net-dns-sec — Perl XS module (Makefile.PL + XS).

Build system: perl Makefile.PL + make + make install
XS module: SEC.xs → SEC.c → SEC.so (links against libcrypto)
Dependencies: OpenSSL (libcrypto), Net::DNS (Perl module)
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlnetdnssecConan(ConanFile):
    name = "perl-net-dns-sec"
    version = "1.26-r2"
    description = "DNSSEC extensions to Net::DNS (Perl XS module with libcrypto)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-DNS-SEC"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Detect Perl version dynamically (e.g., "5.42.0")
        # Use full path because subprocess doesn't inherit Conan profile's [buildenv] PATH
        perl_bin = "/data/service/hnp/bin/perl"
        perl_ver = subprocess.check_output(
            [perl_bin, "-MConfig", "-e", "print $Config{version}"],
            text=True
        ).strip()

        # Step 0: Remove any previously installed version to prevent
        # Makefile.PL's custom install() from detecting occlusion
        site_arch = os.path.join(
            os.path.expanduser("~"),
            f"usr/local/lib/site_perl/{perl_ver}/aarch64-linux"
        )
        for path in [
            os.path.join(site_arch, "Net", "DNS", "SEC.pm"),
            os.path.join(site_arch, "Net", "DNS", "SEC"),
            os.path.join(site_arch, "auto", "Net", "DNS", "SEC"),
        ]:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)

        # Set LD_LIBRARY_PATH so lld can find libxml2.so.16 and runtime libcrypto
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        crypto_lib = "/data/service/hnp/bind.org/bind_9.18.21/lib"
        existing_ldlp = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = (
            f"{llvm_lib}:{crypto_lib}:{existing_ldlp}"
            if existing_ldlp
            else f"{llvm_lib}:{crypto_lib}"
        )

        # Step 1: Generate Makefile via Makefile.PL
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Patch Makefile for OpenHarmony platform
        #   a) Add sysroot include path for system headers (sys/types.h etc.)
        #   b) Add OpenSSL header path for crypto headers
        #   c) Add CRT workaround + libcrypto link
        makefile_path = os.path.join(self.source_folder, "Makefile")
        with open(makefile_path, "r") as f:
            content = f.read()

        sysroot_inc = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include"
        openssl_inc = "/data/service/hnp/node.org/node_v24.13.0/include/node"
        content = re.sub(
            r"^(CCFLAGS = -D_GNU_SOURCE)",
            rf"CCFLAGS = -isystem {sysroot_inc} -isystem {openssl_inc} -D_GNU_SOURCE",
            content,
            flags=re.MULTILINE,
        )
        # -l:libcrypto.so.3 because only libcrypto.so.3 exists (no libcrypto.so symlink)
        content = re.sub(
            r"^LDDLFLAGS = -shared -O2 -fstack-protector-strong$",
            f"LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc -L{crypto_lib} -l:libcrypto.so.3 -O2 -fstack-protector-strong",
            content,
            flags=re.MULTILINE,
        )

        with open(makefile_path, "w") as f:
            f.write(content)

        # Step 3: Build
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        dest = os.path.join(self.package_folder, "")
        self.run(f"make install DESTDIR={dest}", cwd=self.source_folder)

        # Use Perl's Config to find the actual install path dynamically
        perl_bin = "/data/service/hnp/bin/perl"
        install_sitearch = subprocess.check_output(
            [perl_bin, "-MConfig", "-e", "print $Config{installsitearch}"],
            text=True
        ).strip()

        so_src = os.path.join(
            dest, install_sitearch.lstrip("/"),
            "auto", "Net", "DNS", "SEC", "SEC.so"
        )
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        if os.path.isfile(so_src):
            shutil.copy2(so_src, os.path.join(lib_dst, "SEC.so"))

    def package_info(self):
        self.cpp_info.libs = ["SEC"]
        self.cpp_info.libdirs = ["lib"]
