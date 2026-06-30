#!/usr/bin/env python3
"""Conan recipe — cspice 67 (NAIF SPICE Toolkit for C).

cspice uses a custom Makefile (not autotools). The GitHub mirror source
does not include a Makefile, so this recipe generates one during build.

R26: Static linking enforced (BUILD_SHARED_LIBS=OFF).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout


class CspiceConan(ConanFile):
    name = "cspice"
    version = "67"
    description = "Observation geometry system for robotic space science missions (NAIF SPICE Toolkit for C)"
    license = "NAIF"  # NAIF custom license
    homepage = "https://naif.jpl.nasa.gov/naif/toolkit_C.html"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: BUILD_SHARED_LIBS=OFF — cspice is always built as a static library
        pass

    def build(self):
        apply_conandata_patches(self)
        # Generate Makefile since the source doesn't include one
        # Note: Makefile recipes require actual TAB characters
        # Library is named libcspice.a for CMake/Conan compatibility
        makefile_lines = [
            "CC ?= cc",
            "AR ?= ar",
            "CFLAGS ?= -O2",
            "INCLUDES = -I./include",
            "ARFLAGS = r",
            "",
            "SRC_DIR = src",
            "INCLUDE_DIR = include",
            "LIB_DIR = lib",
            "",
            "SRCS = $(wildcard $(SRC_DIR)/*.c)",
            "OBJS = $(SRCS:.c=.o)",
            "LIB = $(LIB_DIR)/libcspice.a",
            "",
            "all: $(LIB)",
            "",
            "$(LIB): $(OBJS)",
            "\t@mkdir -p $(LIB_DIR)",
            "\t$(AR) $(ARFLAGS) $@ $^",
            "\tranlib $@",
            "",
            "%.o: %.c",
            "\t$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@",
            "",
            "install:",
            "\t@mkdir -p $(DESTDIR)$(PREFIX)/lib",
            "\t@mkdir -p $(DESTDIR)$(PREFIX)/include",
            "\tcp $(LIB) $(DESTDIR)$(PREFIX)/lib/",
            "\tcp $(INCLUDE_DIR)/*.h $(DESTDIR)$(PREFIX)/include/",
            "",
            "check:",
            "\t@echo \"Build successful - libcspice.a created\"",
            "",
            "clean:",
            "\trm -f $(SRC_DIR)/*.o $(LIB)",
            "",
        ]
        save(self, os.path.join(self.source_folder, "Makefile"), "\n".join(makefile_lines))
        # Build with the environment's CC and CFLAGS
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "-fPIC -O2")
        if self.options.get_safe("fPIC", True):
            if "-fPIC" not in cflags:
                cflags += " -fPIC"
        self.run(f'make CC="{cc}" CFLAGS="{cflags}" -j1', cwd=self.source_folder)

    def package(self):
        # Copy static library (named libcspice.a for CMake/Conan compatibility)
        copy(self, "libcspice.a", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        # Copy headers
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["cspice"]
