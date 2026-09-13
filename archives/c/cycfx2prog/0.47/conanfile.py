#!/usr/bin/env python3
"""Conan recipe — cycfx2prog 0.47

CycFX2Prog is a small command line tool that programs the Cypress EZ-USB
FX2/FX2LP controller: it downloads 8051 firmware (Intel HEX) into the device
RAM over USB, resets/starts the 8051, and offers bulk/control endpoint
commands for generic USB protocol testing.

Build system: plain hand-written Makefile. There is no `configure`, and the
Makefile only defines `all`, `clean`, `distclean` and `dist` — no `check`,
`test` or `install` target and no upstream test suite (the tarball is four
files: Makefile + two .cc + one .h).

Dependency: upstream uses the libusb-0.1 API (`#include <usb.h>`, `-lusb`).
On OHOS that API is provided by libusb-compat/0.1.7, which is a compat shim
over libusb/1.0.27 (the only libusb flavour published for OHOS).

Flag plumbing: the upstream Makefile assigns ``CFLAGS`` and ``LDFLAGS`` with
``=`` (makefile assignment), so environment variables with the same names are
ignored. The Conan toolchain flags are therefore passed as *make command line
variables*, which by make's precedence rules override the makefile
assignments. That also means the CLI's version string define has to be emitted
by this recipe: ``-DCYCFX2PROG_VERSION=\\"0.47\\"`` (the backslash escaping is
required because the value goes through make and then through the recipe
shell, so a single level of quoting would be eaten twice and the macro would
collapse into a floating point constant).

License: GPL-2.0-only (source headers: "GNU General Public License version 2").
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


def _unique(items):
    """Order-preserving de-duplication (link order of -l flags matters)."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


class Cycfx2progConan(ConanFile):
    name = "cycfx2prog"
    version = "0.47"
    description = ("Command line programmer and endpoint test tool for the "
                   "Cypress EZ-USB FX2/FX2LP — downloads 8051 firmware over USB")
    license = "GPL-2.0-only"
    homepage = "https://www.triplespark.net/elec/periph/USB-FX2/software/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libusb-0.1 API (<usb.h>, -lusb) implemented on top of libusb/1.0.27.
        self.requires("libusb-compat/0.1.7")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cycfx2prog {self.version} needs a libusb backend; "
                f"{self.settings.os} is not supported by this recipe")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def _dependency_flags(self):
        """Collect -I / -L / -l inputs from the recipe's dependency graph."""
        includedirs, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            cppinfo = dep.cpp_info.aggregated_components()
            includedirs.extend(cppinfo.includedirs)
            libdirs.extend(cppinfo.libdirs)
            libs.extend(cppinfo.libs)
        return _unique(includedirs), _unique(libdirs), _unique(libs)

    def build(self):
        apply_conandata_patches(self)

        tc = GnuToolchain(self)
        compiler_executables = self.conf.get("tools.build:compiler_executables",
                                             default={}, check_type=dict)
        cc = compiler_executables.get("c") or "clang"

        includedirs, libdirs, libs = self._dependency_flags()

        # GnuToolchain.defines returns bare macro names (no -D prefix).
        cflags = list(tc.cflags) + [f"-D{d}" for d in tc.defines]
        cflags += [f"-I{d}" for d in includedirs]
        # Flags upstream's own Makefile CFLAGS carries (behaviour preserved).
        cflags += ["-fno-rtti", "-fno-exceptions", "-W", "-Wall", "-Wformat"]
        # Version string macro; see the module docstring for the escaping.
        cflags += [f'-DCYCFX2PROG_VERSION=\\"{self.version}\\"']

        ldflags = list(tc.ldflags) + [f"-L{d}" for d in libdirs]
        ldflags += [f"-l{lib}" for lib in libs]

        command = "make -j1 CC='{cc}' CFLAGS='{cflags}' LDFLAGS='{ldflags}'".format(
            cc=cc, cflags=" ".join(cflags), ldflags=" ".join(ldflags))
        self.output.info(f"build command: {command}")
        self.run(command, cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "cycfx2prog",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command line tool: no library, no headers.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
