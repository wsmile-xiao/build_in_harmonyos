#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""libnids/1.24 — Conan 2 recipe for HarmonyOS (OHOS) aarch64.

libnids (Network Intrusion Detection System library) implements E-commerce
IP defragmentation and TCP stream reassembly on top of libpcap.

Upstream: https://libnids.sourceforge.io/ (Rafal Wojtczuk / Nergal).
Build system: autotools (configure + hand-written Makefile-in).

Upstream 1.24 has no test harness (no `make check`, no tests/ dir, no
ctest/meson); samples/ are live-capture demos needing root + a real NIC.
Verification is therefore entirely consumer-side (test_package) with a
deterministic offline pcap fixture.
"""

import glob
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir
from conan.tools.layout import basic_layout


class LibnidsConan(ConanFile):
    name = "libnids"
    version = "1.24"
    description = "Network Intrusion Detection System library: IP defragmentation and TCP stream reassembly on top of libpcap"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/atomgit-lang/libnids"
    homepage = "https://libnids.sourceforge.io/"
    topics = ("nids", "network", "ids", "pcap", "tcp", "reassembly")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def export(self):
        copy(self, "LICENSE", src=self.recipe_folder, dst=self.export_folder)

    def requirements(self):
        # nids.h #includes <pcap.h> unconditionally; libnids.a/.so call pcap_*.
        self.requires("libpcap/1.10.6", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._check_ohos_toolchain()

        # Autotools build with the Conan-provided libpcap.
        # Upstream Makefile.in PCAPLIB probing is single-root and cross-host
        # blind; override PCAPLIB explicitly on the make command line.
        libpcap = self.dependencies["libpcap"]
        pcap_inc = libpcap.cpp_info.aggregated_components().includedirs[0]
        pcap_libdir = libpcap.cpp_info.aggregated_components().libdirs[0]

        shim_dir = self._make_shim()

        # Repo convention (see add-determinism/0.7.3): mutate os.environ and
        # run with env="conanbuild" so the vars propagate to configure/make.
        os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
        cc = os.environ.get("CC", "clang")
        os.environ["CC"] = cc
        os.environ["CFLAGS"] = "{} -I{}".format(os.environ.get("CFLAGS", ""), pcap_inc).strip()
        os.environ["LDFLAGS"] = "{} -L{}".format(os.environ.get("LDFLAGS", ""), pcap_libdir).strip()
        os.environ["LIBS"] = (os.environ.get("LIBS", "") + " -lpcap").strip()

        configure = os.path.join(self.source_folder, "configure")
        cmd = ["sh", configure,
               "--host=aarch64-linux-ohos",
               "--prefix={}".format(self.package_folder),
               "--disable-libglib",
               "--disable-libnet"]
        if self.options.shared:
            cmd.append("--enable-shared")
        self.output.info("configure: {}".format(" ".join(cmd)))
        self.run(" ".join(cmd), env="conanbuild", cwd=self.source_folder)

        make_target = "shared" if self.options.shared else "static"
        # PCAPLIB must carry -L<pcap libdir> for the shared link (patch 0003
        # adds $(LDFLAGS), but PCAPLIB itself only carries -lpcap when the
        # LIBS-probe path was taken).
        pcaplib = "-L{} -lpcap".format(pcap_libdir)
        self.run('make -j1 {} PCAPLIB="{}"'.format(make_target, pcaplib),
                 env="conanbuild", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        mkdir(self, os.path.join(self.package_folder, "lib"))
        mkdir(self, os.path.join(self.package_folder, "include"))
        # upstream `make install` installs nids.h + lib + man; do it manually
        # (safer than relying on autotools paths under cross prefix).
        copy(self, "nids.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        for pat in ("libnids.a", "libnids.so*", "libnids.la"):
            for f in glob.glob(os.path.join(self.source_folder, "src", pat)):
                copy(self, os.path.basename(f), src=os.path.dirname(f),
                     dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            # linker output is libnids.so.1.24 (SONAME); create the plain
            # `libnids.so` symlink so -lnids / CMakeDeps find it.
            so_dir = os.path.join(self.package_folder, "lib")
            soname = "libnids.so.1.24"
            if os.path.isfile(os.path.join(so_dir, soname)):
                link = os.path.join(so_dir, "libnids.so")
                if not os.path.lexists(link):
                    os.symlink(soname, link)

    def package_info(self):
        self.cpp_info.libs = ["nids"]
        if self.options.shared:
            # The shared lib is linked against the static libpcap archive
            # (libpcap/1.10.6 ohos package ships .a only), so pcap_* symbols
            # are absorbed into libnids.so — consumers don't link libpcap.
            pass
        else:
            # Static libnids.a references pcap_*; consumers must link libpcap
            # (declared transitive_headers/transitive_libs via requires()).
            self.cpp_info.requires = ["libpcap::libpcap"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("pkg_config_name", "libnids")

    # ------------------------------------------------------------------
    def _check_ohos_toolchain(self):
        if str(self.settings.os) != "OHOS":
            return
        cc = os.environ.get("CC", "clang")
        if not shutil.which(cc):
            raise ConanInvalidConfiguration(
                "OHOS build requires a working CC (clang) in PATH; got CC={!r}".format(cc)
            )

    def _make_shim(self):
        """Create a directory with an `install` shim because the OHOS
        SDK's llvm-install tool is not on PATH; the real `install` (coreutils)
        does not know OHOS sysroot flags. We rely on `cp` instead."""
        # not needed for our manual package() copy; kept for future use
        return os.path.join(self.build_folder, "shim")
