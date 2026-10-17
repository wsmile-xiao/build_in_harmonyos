#!/usr/bin/env python3
"""Conan recipe — pazpar2 1.14.1 (autotools, Index Data metasearch engine)."""
import os
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Pazpar2Conan(ConanFile):
    name = "pazpar2"
    version = "1.14.1"
    description = "Pazpar2 metasearch engine: Z39.50/SRU/Solr aggregation and result normalisation server"
    license = "GPL-2.0-or-later"
    homepage = "https://www.indexdata.com/resources/software/pazpar2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # yaz: Z39.50 / SRU toolkit, published in the ohpcd registry.
        self.requires("yaz/5.37.3", transitive_headers=True, transitive_libs=True)
        # pazpar2 uses libxslt/libxml2 directly (normalize_record.c, service_xslt.c,
        # settings.c, pazpar2_config.c, marcmap.c, marchash.c, session.c).
        self.requires("libxslt/1.1.45.2")
        self.requires("libxml2/2.15.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports Linux and OHOS only (got os={self.settings.os})")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # The release tarball is an autotools `make dist` output shipped with
        # pre-generated configure/aclocal.m4/Makefile.in. Patching configure.ac
        # makes it newer than those vendored files, so `make` would try to
        # re-run aclocal/automake/autoheader — not available in the OHOS build
        # environment. Re-stamp the generated files so the regeneration rules
        # never trigger; the build then uses the shipped configure verbatim.
        stamp = time.time_ns()
        generated = ("aclocal.m4", "configure", "config.h.in", "Doxyfile.in",
                     "Makefile.in", "confdefs.h", "config.status")
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                if name in generated:
                    os.utime(os.path.join(root, name), ns=(stamp, stamp))

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Upstream ships an autotools `make dist` tarball: no autoreconf needed.
        # config.guess/config.sub are patched to recognise HarmonyOS (Linux-like),
        # so no --build/--host override is required.
        tc.configure_args.append("--disable-dependency-tracking")
        # pazpar2 locates YAZ through the upstream `yaz-config` script
        # (configure.ac -> YAZ_INIT -> YAZ_CONFIG). The yaz package does not
        # export its bin/ through buildenv_info, so point configure at it
        # explicitly instead of relying on PATH.
        yaz_bin = os.path.join(self.dependencies["yaz"].package_folder, "bin")
        tc.configure_args.append(f"--with-yaz={yaz_bin}")
        # libxml2 is consumed as a shared library from the registry (libxml2.so.16).
        # Configure runs its probes by executing freshly linked conftest binaries,
        # so the dependency libdirs have to be reachable by the loader at build
        # time (LD_LIBRARY_PATH is not part of the autotools build env) as well as
        # at run time for the produced binaries.
        for dep in self.dependencies.host.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS: the GNU make jobserver cannot create its FIFO, keep it serial.
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
