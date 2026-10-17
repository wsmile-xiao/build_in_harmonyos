#!/usr/bin/env python3
"""Conan recipe for s6-dns 2.4.1.0 — skarnet.org DNS resolution library and tools.

s6-dns uses skarnet's own configure + make system (not standard autotools/cmake).
It depends on skalibs, which is also a skarnet.org package.
Since skalibs is not published to the conan registry, this recipe
builds skalibs from source first, then builds s6-dns against it.

The package produces both static libraries (libs6dns.a, libskadns.a) and
command-line tools (s6-dnsq, s6-dnsqr, s6-dnsip, s6-dnsmx, etc.).
"""
import os
import shutil
import tarfile
import urllib.request
import time
import hashlib

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class S6DnsConan(ConanFile):
    name = "s6-dns"
    version = "2.4.1.0"
    description = "skarnet.org s6-dns — DNS resolution library and tools (s6-dnsq, s6-dnsqr, s6-dnsip, etc.)"
    license = "ISC"
    homepage = "https://skarnet.org/software/s6-dns/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def _download_with_retry(self, url, dest, retries=3):
        urls = url if isinstance(url, list) else [url]
        last_err = None
        for u in urls:
            for attempt in range(retries):
                try:
                    urllib.request.urlretrieve(u, dest)
                    return
                except Exception as e:
                    last_err = e
                    if attempt < retries - 1:
                        time.sleep(2)
        raise last_err

    def source(self):
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        archive_path = os.path.join(self.export_sources_folder, "s6-dns.tar.gz")
        if not os.path.exists(archive_path):
            self.output.info(f"Downloading s6-dns source from {url}")
            self._download_with_retry(url, archive_path)
        h = hashlib.sha256()
        with open(archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        if h.hexdigest() != sha256:
            raise Exception(f"SHA256 mismatch: expected {sha256}")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=self.source_folder)
        extracted_dir = os.path.join(self.source_folder, f"s6-dns-{self.version}")
        if os.path.isdir(extracted_dir):
            for item in os.listdir(extracted_dir):
                src = os.path.join(extracted_dir, item)
                dst = os.path.join(self.source_folder, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)
            os.rmdir(extracted_dir)

    def build(self):
        apply_conandata_patches(self)
        stage_dir = os.path.join(self.build_folder, "stage")
        os.makedirs(stage_dir, exist_ok=True)

        # Step 1: Build skalibs
        # Use mirror fallback for CI workers with restricted network
        skalibs_url = [
            "https://gh-proxy.com/https://github.com/skarnet/skalibs/archive/refs/tags/v2.15.1.0.tar.gz",
            "https://github.com/skarnet/skalibs/archive/refs/tags/v2.15.1.0.tar.gz",
        ]
        skalibs_archive = os.path.join(self.build_folder, "skalibs.tar.gz")
        if not os.path.exists(skalibs_archive):
            self.output.info("Downloading skalibs source...")
            self._download_with_retry(skalibs_url, skalibs_archive)
        skalibs_src = os.path.join(self.build_folder, "skalibs-2.15.1.0")
        if not os.path.isdir(skalibs_src):
            with tarfile.open(skalibs_archive, "r:gz") as tar:
                tar.extractall(path=self.build_folder)
        self.output.info("Building skalibs...")
        # Patch: on some CI workers the linker (lld) doesn't support GNU ld
        # flags, causing skalibs configure to fail on socket function detection.
        # On Linux/OHOS socket functions are in libc, so no extra libs needed.
        import re
        configure_path = os.path.join(skalibs_src, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        content = content.replace(
            "socket_lib=`detectlibs lsock -lsocket -lnsl` || fail \"$0: unable to determine required linker flags for socket functions\"",
            'socket_lib=""\necho "  ... none (patched for OHOS)"'
        )
        with open(configure_path, "w") as f:
            f.write(content)
        self.run(f"cd {skalibs_src} && "
                 f"./configure --prefix={stage_dir} --disable-shared "
                 f"CPPFLAGS=-I{stage_dir}/include LDFLAGS=-L{stage_dir}/lib",
                 env="conanbuild")
        self.run(f"cd {skalibs_src} && make -j1", env="conanbuild")
        self.run(f"cd {skalibs_src} && make install", env="conanbuild")

        # Step 2: Build s6-dns
        self.output.info("Building s6-dns...")
        s6dns_src = self.source_folder
        self.run(f"cd {s6dns_src} && "
                 f"./configure --prefix={stage_dir} --disable-shared "
                 f"--with-sysdeps={stage_dir}/lib/skalibs/sysdeps "
                 f"--with-include={stage_dir}/include "
                 f"--with-lib={stage_dir}/lib "
                 f"CPPFLAGS=-I{stage_dir}/include LDFLAGS=-L{stage_dir}/lib",
                 env="conanbuild")
        self.run(f"cd {s6dns_src} && make -j1", env="conanbuild")
        self.run(f"cd {s6dns_src} && make install", env="conanbuild")

    def package(self):
        stage_dir = os.path.join(self.build_folder, "stage")
        bin_dir = os.path.join(stage_dir, "bin")
        if os.path.isdir(bin_dir):
            copy(self, "*", bin_dir, os.path.join(self.package_folder, "bin"))
        lib_dir = os.path.join(stage_dir, "lib")
        if os.path.isdir(lib_dir):
            copy(self, "*.a", lib_dir, os.path.join(self.package_folder, "lib"))
        inc_dir = os.path.join(stage_dir, "include")
        if os.path.isdir(inc_dir):
            copy(self, "*", inc_dir, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["s6dns", "skadns", "skarnet"]
