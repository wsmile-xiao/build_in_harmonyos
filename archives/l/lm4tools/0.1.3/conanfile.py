#!/usr/bin/env python3
"""Conan recipe for lm4tools 0.1.3 (Stellaris LaunchPad tools, HarmonyOS PC).

Upstream (utzig/lm4tools) is a raw Makefile project with two independent
sub-projects, each producing a command line tool:

* ``lm4flash/``  -> ``lm4flash``: firmware flasher over USB (libusb-1.0)
* ``lmicdiusb/`` -> ``lmicdi``:   GDB<->USB debug bridge (libusb-1.0 + POSIX)

Neither Makefile knows OHOS: ``lm4flash`` falls through to a ``pkg-config``
probe and ``lmicdiusb`` matches only Darwin/FreeBSD/Linux via
``ifeq ($(shell uname),...)``, so on HarmonyOS (uname = "HarmonyOS") the
libusb variables are empty and the link fails with undefined references.

Both problems are solved without patching the sources: the recipe passes
explicit ``CFLAGS``/``LDFLAGS`` (lm4flash) and ``LIBUSB_CFLAGS``/
``LIBUSB_LIBDIR``/``LIBUSB_LIBS`` (lmicdiusb) on the make command line,
built from the libusb dependency's ``cpp_info`` (never from the package's
unrelocated ``libusb-1.0.pc``, whose prefix points at /usr/local — notes.md
problem 3).

E392 trap 3: the Makefiles live in the extracted source, so every ``make``
runs with ``cwd=`` the respective sub-project directory, not build_folder.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Lm4ToolsConan(ConanFile):
    name = "lm4tools"
    version = "0.1.3"
    description = (
        "Tools for TI Stellaris / Tiva C LaunchPad boards: lm4flash firmware "
        "flasher and lmicdi GDB-USB debug bridge (libusb-1.0 based)"
    )
    license = "MIT"  # lm4flash is MIT; lmicdiusb is BSD-3-Clause (TI) — see notes.md
    homepage = "https://github.com/utzig/lm4tools"
    package_type = "application"

    # application package: no options, it makes no sense to build a "shared"
    # or header-only variant of two CLI executables
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libusb/1.0.27")

    def validate(self):
        # R32: OHOS accepted alongside Linux, never "== Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lm4tools supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        # E392-1: explicit filename keeps get() from guessing the decoder
        # from the URL suffix; strip_root drops the lm4tools-0.1.3/ prefix.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="lm4tools-0.1.3.tar.gz")

    def _compiler(self):
        # E392-2: compiler_executables is a dict {'c':..,'cpp':..}, fetch the
        # whole dict with check_type=dict then .get("c").
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def _libusb_paths(self):
        """(include_dir, lib_dir) of the libusb dependency package."""
        dep = self.dependencies.get("libusb")
        if dep is None:
            raise ConanInvalidConfiguration("libusb dependency missing from the graph")
        include = os.path.join(dep.cpp_info.includedirs[0])
        lib = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        return include, lib

    def build(self):
        apply_conandata_patches(self)
        compiler = self._compiler()
        include, lib = self._libusb_paths()

        optimization_flags = {
            "Debug": "-g -O0",
            "Release": "-O2",
            "RelWithDebInfo": "-g -O2",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")

        # lm4flash: Makefile only special-cases FreeBSD; every other OS runs
        # `pkg-config --cflags/--libs libusb-1.0`.  OHOS has no system-wide
        # pkg-config index for the conan libusb package (the package's .pc is
        # un-relocated), so inject both flags explicitly.  `CC ?= gcc` is a
        # command-line override, and the hardcodes never apply.
        lm4flash_dir = os.path.join(self.source_folder, "lm4flash")
        self.run(
            'make -j1 CC="{cc}" CFLAGS="-Wall {opt} -I{inc}" '
            'LDFLAGS="-L{lib} -lusb-1.0"'.format(
                cc=compiler, opt=optimization_flags, inc=include, lib=lib),
            cwd=lm4flash_dir,
        )

        # lmicdiusb: the Makefile matches only Darwin/FreeBSD/Linux via
        # `ifeq ($(shell uname),...)`; on HarmonyOS none matches, so all three
        # libusb variables are empty and the link fails with undefined
        # references.  All three are plain `:= / ?=` assignments, i.e.
        # overridable from the make command line, so we pass them explicitly.
        # The `#` or `:` in paths would need quoting; paths here contain none.
        lmicdi_dir = os.path.join(self.source_folder, "lmicdiusb")
        self.run(
            'make -j1 CC="{cc}" LIBUSB_CFLAGS="-I{inc}" '
            'LIBUSB_LIBDIR="{lib}" LIBUSB_LIBS="-lusb-1.0"'.format(
                cc=compiler, inc=include, lib=lib),
            cwd=lmicdi_dir,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "lm4flash", src=os.path.join(self.source_folder, "lm4flash"),
             dst=bin_dir, keep_path=False)
        copy(self, "lmicdi", src=os.path.join(self.source_folder, "lmicdiusb"),
             dst=bin_dir, keep_path=False)

        for tool in ("lm4flash", "lmicdi"):
            binary = os.path.join(bin_dir, tool)
            if not os.path.isfile(binary):
                raise ConanInvalidConfiguration(
                    f"lm4tools executable was not produced by the build: {binary}"
                )

        # lm4tools links libusb dynamically; the dependency's .so must be
        # found at runtime.  The test_package uses VirtualRunEnv, which
        # extends PATH/LD_LIBRARY_PATH from the dependency graph, so no extra
        # rpath is embedded into the binaries.
        for tool in ("lm4flash", "lmicdi"):
            os.chmod(os.path.join(bin_dir, tool), 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
