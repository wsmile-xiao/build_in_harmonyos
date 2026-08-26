#!/usr/bin/env python3
"""Conan recipe for exodriver (liblabjackusb) 2.7.0.

Exodriver is a LabJack USB device access library (liblabjackusb) built with a
raw Makefile (no configure/autotools/cmake). The build target lives in the
liblabjackusb/ subdirectory.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ExodriverConan(ConanFile):
    name = "exodriver"
    version = "2.7.0"
    description = "LabJack USB device access library (liblabjackusb)"
    license = "X11"
    homepage = "https://github.com/labjack/exodriver"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        ar = comp_execs.get("ar") or "llvm-ar"
        ranlib = comp_execs.get("ranlib") or "llvm-ranlib"

        # libusb dependency paths from Conan
        libusb = self.dependencies["libusb"]
        # libusb sets includedirs=["include/libusb-1.0"], but exodriver source
        # uses #include <libusb-1.0/libusb.h>, so we need the parent "include" dir.
        libusb_inc = os.path.join(libusb.package_folder, "include")
        libusb_lib = libusb.cpp_info.libdirs[0]

        # Build in the liblabjackusb subdirectory
        build_dir = os.path.join(self.source_folder, "liblabjackusb")

        cflags = f"-fPIC -O2 -I{libusb_inc}"
        libflags = f"-L{libusb_lib} -lusb-1.0 -lc"

        # R9: Always use -j1
        self.run(f'make -C {build_dir} CC="{cc}" AR="{ar}" RANLIB="{ranlib}" '
                 f'CFLAGS="{cflags}" LIBFLAGS="{libflags}" '
                 f'RUN_LDCONFIG=0 -j1')

        if not self.options.shared:
            # Create static library from the compiled object
            self.run(f'{ar} rcs {build_dir}/liblabjackusb.a {build_dir}/labjackusb.o')

    def package(self):
        build_dir = os.path.join(self.source_folder, "liblabjackusb")

        # Headers
        copy(self, "labjackusb.h", build_dir, os.path.join(self.package_folder, "include"))

        if self.options.shared:
            # Shared library: copy liblabjackusb.so.2.7.0 and create symlinks
            copy(self, "liblabjackusb.so*", build_dir, os.path.join(self.package_folder, "lib"))
        else:
            # Static library
            copy(self, "liblabjackusb.a", build_dir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["labjackusb"]
        # libusb is a runtime dependency
        self.cpp_info.requires = ["libusb::libusb"]
