#!/usr/bin/env python3
"""Conan recipe for libdontdie 1.2.0 — LD_PRELOAD TCP-keepalive library.

Upstream is a bare Makefile producing one shared object: no configure
step, no install target, no static build, and no public header.  make(1)
hardcodes CC=gcc with '=', so the OHOS compiler must be passed on the
make command line (an environment CC would be ignored).  The upstream
repo ships hand-driven test programs instead of a test runner: the
non-interactive performance program is executed under LD_PRELOAD inside
build() as the upstream test run; the interactive blackbox pair and the
Java example cannot be driven headlessly and are recorded as skipped in
test_package/MANIFEST.yml and notes.md.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibdontdieConan(ConanFile):
    name = "libdontdie"
    version = "1.2.0"
    description = ("LD_PRELOAD library that enables TCP keepalive with "
                   "configurable parameters on every socket created via socket(2)")
    license = "MIT"
    homepage = "https://github.com/flonatel/libdontdie"
    url = "https://github.com/flonatel/libdontdie"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libdontdie 1.2.0 upstream builds a shared object only")

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        return executables.get("c", os.environ.get("CC", "clang"))

    def build(self):
        apply_conandata_patches(self)
        cc = self._c_compiler()
        src = self.source_folder
        self.run(f"make CC={cc} -j1", cwd=src)
        # Build the upstream test programs (upstream has no test runner).
        self.run(f"{cc} -Wall -o test/Cblackbox/tcp_server test/Cblackbox/tcp_server.c",
                 cwd=src)
        self.run(f"{cc} -Wall -o test/Cblackbox/tcp_client test/Cblackbox/tcp_client.c",
                 cwd=src)
        self.run(f"{cc} -Wall -O3 -o test/Cperformance/perf test/Cperformance/perf.c",
                 cwd=src)
        # Real upstream test execution: run the non-interactive perf program
        # with the freshly built library preloaded; every one of the 1000
        # socket() calls must be intercepted and configured with keepalive.
        self.run(
            "DD_TCP_KEEPALIVE_TIME=4 DD_TCP_KEEPALIVE_INTVL=5 "
            "DD_TCP_KEEPALIVE_PROBES=6 LD_PRELOAD=./libdontdie.so "
            "./test/Cperformance/perf 1000",
            cwd=src)

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "libdontdie.so", src=self.source_folder, dst=libdir,
             keep_path=False)
        # Recreate the soname symlink explicitly: conan.tools.files.copy
        # would copy a symlink as a duplicate of its target file.
        os.symlink("libdontdie.so", os.path.join(libdir, "libdontdie.so.0"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["dontdie"]
