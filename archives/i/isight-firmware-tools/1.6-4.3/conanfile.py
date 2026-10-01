#!/usr/bin/env python3
"""Conan recipe for isight-firmware-tools 1.6-4.3.

Apple's built-in iSight webcam needs firmware extracted from the Mac OS X
``AppleUSBVideoSupport`` driver.  This package provides three programs:

* ``ift-extract`` -- find and extract the firmware from the driver file;
* ``ift-export``  -- convert the extracted firmware to Intel HEX;
* ``ift-load``    -- upload the firmware to the camera over USB (libusb).

The upstream tarball is autotools-generated (``configure``/``Makefile.in``),
but its 2012 ``configure`` predates both aarch64 and HarmonyOS (``config.sub``
is not even shipped), and it pulls in intltool/gettext at configure time.  To
avoid that whole bootstrap chain this recipe compiles the three programs
directly with the OHOS clang, providing a minimal ``config.h`` -- exactly the
approach already used for sxid / libblocksruntime. Dependencies are the same
libraries ``configure`` would have found via pkg-config: glib-2.0, libgcrypt
and libusb-compat (usb.h), plus gettext-tiny for the intl macros glib's
``gi18n.h`` requires.

There is no upstream test suite: ``tests/Makefile.am`` only loops over
``AppleUSBVideoSupport*`` files that are not shipped.  ``test_package`` drives
the installed programs, including a real Intel-HEX conversion of a synthetic
firmware image.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

CONFIG_H = """\
/* Minimal config.h for the OHOS build (no autotools).
 * glib 2.84's gi18n.h unconditionally includes <libintl.h> and expands the
 * `_()` macro to gettext(); the OHOS sysroot libintl.h is only a stub, so the
 * gettext-tiny dependency supplies the real header and static libintl.a. */
#define PACKAGE "isight-firmware-tools"
#define PACKAGE_NAME "isight-firmware-tools"
#define PACKAGE_VERSION "1.6"
#define VERSION "1.6"
#define GETTEXT_PACKAGE "isight-firmware-tools"
#define PACKAGE_LOCALE_DIR "/usr/share/locale"
#define PACKAGE_BUGREPORT "https://bugs.launchpad.net/isight-firmware-tools"
"""


class IsightFirmwareToolsConan(ConanFile):
    name = "isight-firmware-tools"
    version = "1.6-4.3"
    description = ("Tools for extracting and loading the firmware of Apple's "
                   "built-in iSight webcam")
    license = "GPL-2.0-or-later"
    homepage = "https://launchpad.net/isight-firmware-tools/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "isight-firmware-tools is validated on Linux/OHOS only, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libgcrypt/1.11.0")
        self.requires("libusb-compat/0.1.7")
        # glm 2.84's gi18n.h unconditionally includes <libintl.h> and expands
        # `_()` to gettext(), while the OHOS sysroot libintl.h is a bare stub.
        # gettext-tiny provides the real libintl.h (and static libintl.a).
        self.requires("gettext-tiny/0.3.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _dep_flag(self, dep_name, kind):
        dep = self.dependencies.get(dep_name)
        if dep is None:
            return ""
        try:
            ci = dep.cpp_info.aggregated_components()
        except Exception:
            ci = dep.cpp_info
        values = []
        if kind == "cflags":
            for d in ci.includedirs:
                values.append("-I" + (d if os.path.isabs(d) else os.path.join(dep.package_folder, d)))
        else:
            for d in ci.libdirs:
                values.append("-L" + (d if os.path.isabs(d) else os.path.join(dep.package_folder, d)))
            values += ["-l" + lib for lib in ci.libs]
            values += ["-l" + lib for lib in ci.system_libs]
        return " ".join(values)

    def _flags(self, kind):
        deps = ("glib", "libgcrypt", "libgpg-error", "libusb-compat", "libusb",
                "gettext-tiny")
        return " ".join(filter(None, (self._dep_flag(d, kind) for d in deps)))

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cc = self._compiler("c", "clang")
        with open(os.path.join(src, "config.h"), "w", encoding="utf-8") as handle:
            handle.write(CONFIG_H)
        cflags = "-DHAVE_CONFIG_H -O2 -Wall -I. " + self._flags("cflags")
        libs = self._flags("libs")
        self.run('{} {} -o ift-extract src/extract.c {}'.format(cc, cflags, libs), cwd=src)
        self.run('{} {} -o ift-export src/export.c {}'.format(cc, cflags, libs), cwd=src)
        self.run('{} {} -o ift-load src/udev.c src/load.c {}'.format(cc, cflags, libs), cwd=src)
        for prog in ("ift-extract", "ift-export", "ift-load"):
            if not os.path.isfile(os.path.join(src, prog)):
                raise ConanInvalidConfiguration(
                    "build did not produce the '{}' program".format(prog))

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for prog in ("ift-extract", "ift-export", "ift-load"):
            copy(self, prog, self.source_folder, bin_dir)
        copy(self, "doc/*.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        for doc in ("README", "NEWS", "HOWTO"):
            copy(self, doc, self.source_folder,
                 os.path.join(self.package_folder, "share", "doc", "isight-firmware-tools"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
