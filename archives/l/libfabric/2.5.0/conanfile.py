#!/usr/bin/env python3
"""Conan recipe — libfabric 2.5.0 (Autotools).

libfabric (OpenFab Interfaces, OFI) is a high-performance communication
framework library exposing a standard API over multiple network providers
(sockets, TCP, UDP, RXM, SHM, MRail ...).  Upstream uses Autotools
(configure + make).

OHOS adaptation notes (see notes.md / README.md for full detail):
  - --enable-monitor=no : monitor provider pulls in fstab.h, absent on OHOS.
  - config.guess/config.sub patched to recognise the OHOS triplet.
  - src/unix/osd.c guarded with __OHOS__ to skip pthread_setaffinity_np /
    cpu_set_t (musl libc does not provide them).
  - configure mktemp patched to use $TMPDIR (HMDFS cannot create the
    relative-path temp dir "./confXXXXXX").

libfabric is NOT a system same-name library (R26), so shared linking is OK
and Conan manages the dependency chain.
"""
from conan import ConanFile
from conan.tools.files import get, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class LibfabricConan(ConanFile):
    name = "libfabric"
    version = "2.5.0"
    description = "OpenFab Interfaces (OFI) — high-performance communication framework library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/ofiwg/libfabric"
    url = "https://github.com/ofiwg/libfabric"
    topics = ("fabric", "ofi", "rdma", "hpc", "networking")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libfabric has no Conan-managed dependencies in this build.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: libfabric is NOT a system same-name library — shared linking OK.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable the monitor provider: it requires fstab.h, which OHOS does
        # not provide (see notes.md problem 1).  Harmless on Linux.
        tc.configure_args.append("--enable-monitor=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # R14: remove libtool .la files (residual from autotools install).
        for root, _, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".la"):
                    la = os.path.join(root, f)
                    try:
                        os.remove(la)
                    except OSError:
                        pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libfabric")
        self.cpp_info.set_property("cmake_target_name", "libfabric::libfabric")
        self.cpp_info.set_property("pkg_config_name", "libfabric")
        self.cpp_info.libs = ["fabric"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
