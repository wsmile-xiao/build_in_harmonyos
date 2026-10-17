#!/usr/bin/env python3
"""Conan recipe for readsb 3.16.15 — Mode-S/ADS-B decoder (C11, Makefile).

HarmonyOS PC adaptation:
- Pure C (C11) Makefile build, no autotools/CMake.
- RTLSDR=no by default (SDR hardware support optional; core decoding needs
  only zstd + pthread + rt). BIAS-TEE/HACKRF/etc all off.
- zstd from conan (requires zstd/1.5.7.1, published in main).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.layout import basic_layout


class ReadsbConan(ConanFile):
    name = "readsb"
    version = "3.16.15"
    description = "Mode-S/ADS-B/TIS decoder for RTLSDR, BladeRF, HackRF, SDRplay etc"
    license = "GPL-3.0"
    homepage = "https://github.com/wiedehopf/readsb"
    url = "https://github.com/wiedehopf/readsb"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def requirements(self):
        self.requires("zstd/1.5.7.1")
        self.requires("ncurses/6.6")  # interactive.o needs curses.h

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isfile(os.path.join(self.source_folder, "Makefile")):
            raise ConanException("readsb Makefile not found in source")
        zstd = self.dependencies["zstd"]
        zstd_pkg = zstd.package_folder
        ncurses = self.dependencies["ncurses"]
        ncurses_pkg = ncurses.package_folder
        # Pass values as make COMMAND-LINE variables (VAR=val && make does not
        # export them into make's environment, so $(ZSTD_INCLUDE) would be empty)
        make_args = " ".join(
            f"{k}={v}"
            for k, v in {
                "CC": "clang",
                "ZSTD_INCLUDE": os.path.join(zstd_pkg, "include"),
                "ZSTD_LIB": os.path.join(zstd_pkg, "lib"),
                "NCURSES_INCLUDE": os.path.join(ncurses_pkg, "include"),
                "NCURSES_LIB": os.path.join(ncurses_pkg, "lib"),
                # aarch64: no AVX2/arch-specific codegen; keep SDR hw off
                "RTLSDR": "no",
                "BLADERF": "no",
                "HACKRF": "no",
                "PLUTOSDR": "no",
                "SOAPYSDR": "no",
                "AGGRESSIVE": "no",
            }.items()
        )
        self.run(f'sh -c "make -j1 readsb {make_args}"', cwd=self.source_folder)

    def package(self):
        copy(self, "readsb", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
