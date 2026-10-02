#!/usr/bin/env python3
"""Conan recipe for langford 0.0.20130228.

The ``langford`` package from Per Vices is the host-side software for the
"Noctar" (formerly "Phi") IQ demodulator board.  The Debian source ships three
parts:

* ``langford.c`` / ``langford.h`` -- a Linux **kernel module** (PCIe/DMA).  This
  cannot be built for OHOS (no loadable kernel modules, no ``linux/pci.h``
  device API) and is intentionally not part of this recipe.
* ``langford_util.cpp`` / ``langford_adc_util.cpp`` / ``langford_spi.cpp`` --
  the userspace control utilities (bit-banging over the ``/dev/langford``
  character device via ioctl).
* ``libs/*.cpp`` -- the RF synthesiser (ADF4351) and VGA (LMH6521) programmers.

This recipe builds the userspace utilities and the ``langford_spi`` helper
library.  The kernel module is shipped verbatim as documentation/source only
on the upstream page and is out of scope for a userspace OHOS package.

The upstream tarball is only published over plain HTTP (pervices.com), so the
recipe uses Debian's verbatim ``.orig.tar.bz2`` (same upstream release, HTTPS,
pinned SHA-256).  There is no upstream test suite; ``test_package`` exercises
the installed programs and links a consumer against ``liblangford_spi.a``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

PROGRAMS = (
    "langford_util",
    "langford_adc_util",
    "langford_rf_fsynth",
    "langford_rx_rf_bb_vga",
)


class LangfordConan(ConanFile):
    name = "langford"
    version = "0.0.20130228"
    description = ("Control utilities for the Per Vices Noctar IQ demodulator "
                   "board (userspace tools + SPI helper library)")
    license = "GPL-3.0-or-later"
    homepage = "http://www.pervices.com/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "langford userspace tools are validated on Linux/OHOS only, "
                "not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cxx = self._compiler("cpp", "clang++")
        ar = "llvm-ar"
        # Upstream compiles with `g++ -ansi`; keep C++98 but allow POSIX
        # declarations (ioctl/open) via gnu++98.
        flags = "-std=gnu++98 -O2 -Wall"
        src = self.source_folder
        libs = os.path.join(src, "libs")
        self.run('{} {} langford_util.cpp -o langford_util'.format(cxx, flags), cwd=src)
        self.run('{} {} langford_adc_util.cpp langford_spi.cpp -o langford_adc_util'.format(cxx, flags), cwd=src)
        self.run('{} {} fsynth.cpp -o langford_rf_fsynth'.format(cxx, flags), cwd=libs)
        self.run('{} {} lmh6521.cpp -o langford_rx_rf_bb_vga'.format(cxx, flags), cwd=libs)
        self.run('{} {} -c langford_spi.cpp -o langford_spi.o'.format(cxx, flags), cwd=src)
        self.run('{} rcs liblangford_spi.a langford_spi.o'.format(ar), cwd=src)
        for prog in PROGRAMS:
            path = os.path.join(src, prog)
            if prog in ("langford_rf_fsynth", "langford_rx_rf_bb_vga"):
                path = os.path.join(libs, prog)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    "build did not produce the '{}' program".format(prog))
        if not os.path.isfile(os.path.join(src, "liblangford_spi.a")):
            raise ConanInvalidConfiguration("build did not produce liblangford_spi.a")

        # Upstream userspace testbench (libs/dev/testbench.cpp): a pure
        # in-memory unit test -- integer->binary conversion plus the default
        # ADF4351 register values.  It needs no Noctar hardware, prints
        # "N tests passed, M tests failed" and exits with the failure count,
        # so self.run() enforces a real pass.
        dev = os.path.join(src, "libs", "dev")
        self.run('{} {} testbench.cpp -o testbench'.format(cxx, flags), cwd=dev)
        self.run("./testbench", cwd=dev)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "langford_util", self.source_folder, bin_dir)
        copy(self, "langford_adc_util", self.source_folder, bin_dir)
        copy(self, "langford_rf_fsynth", os.path.join(self.source_folder, "libs"), bin_dir)
        copy(self, "langford_rx_rf_bb_vga", os.path.join(self.source_folder, "libs"), bin_dir)
        copy(self, "liblangford_spi.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        inc_dir = os.path.join(self.package_folder, "include")
        copy(self, "langford_ioctl.h", self.source_folder, inc_dir)
        copy(self, "langford_spi.h", self.source_folder, inc_dir)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["langford_spi"]
