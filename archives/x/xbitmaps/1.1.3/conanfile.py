#!/usr/bin/env python3
"""Conan recipe for xbitmaps 1.1.3 (X11 bitmap data package).

xbitmaps is a *pure data* package: it ships 71 X10/X11 bitmap files in C
source form (``#define <name>_width`` / ``<name>_height`` plus a static
``<name>_bits[]`` array) which upstream installs verbatim into
``$includedir/X11/bitmaps``.  Consumers either ``#include`` them directly
or parse them at runtime (XReadBitmapFile / Xbm loaders).  Nothing is
compiled upstream, so this recipe installs the data files as a
header-library package and validates every bitmap in build() instead.

OHOS notes:
  - Zero patches, zero third-party dependencies, no toolchain involvement.
  - The official tarball host (xorg.freedesktop.org / www.x.org) is flaky
    from CN networks; the conandata URL uses the xorg.freedesktop.org form
    so the CI mirror chain (csclub/mirrorservice/ircam) can kick in.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout

EXPECTED_COUNT = 71


class XbitmapsConan(ConanFile):
    name = "xbitmaps"
    version = "1.1.3"
    description = "X11 bitmap data files used by X clients (pure data package)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/data/xbitmaps"
    url = ""

    # Pure data shipped as includable C snippets: header-library is the
    # closest Conan package type (include path only, nothing to link).
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def package_id(self):
        self.info.clear()

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xbitmaps is only consumed on Linux/OHOS, not %s" % self.settings.os)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _bitmap_names(self):
        """Extract the dist_bitmap_DATA file list from upstream Makefile.am."""
        path = os.path.join(self.source_folder, "Makefile.am")
        names = []
        collecting = False
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not collecting:
                    if line.startswith("dist_bitmap_DATA"):
                        collecting = True
                        line = line.split("=", 1)[1]
                    else:
                        continue
                for tok in line.replace("\\", " ").split():
                    if tok and not tok.startswith("#"):
                        names.append(tok)
                if not line.rstrip().endswith("\\"):
                    break
        return names

    def _validate_bitmap(self, name):
        path = os.path.join(self.source_folder, name)
        if not os.path.isfile(path):
            raise ConanException("bitmap data file missing from source tree: %s" % name)
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        # NB: the macro stem may differ from the file name (upstream quirk:
        # the file "calculator" actually contains the "icon" bitmap), so
        # take the stem from the first <stem>_width define like X11's
        # XReadBitmapFile does.
        mw = re.search(r"^#define\s+(\w+)_width\s+(\d+)\s*$", text, re.M)
        if not mw:
            raise ConanException("bitmap %s lacks a <stem>_width define" % name)
        stem = mw.group(1)
        width = int(mw.group(2))
        mh = re.search(r"^#define\s+%s_height\s+(\d+)\s*$" % re.escape(stem), text, re.M)
        mb = re.search(r"%s_bits\[\]\s*=\s*\{(.*?)\}" % re.escape(stem), text, re.S)
        if not (mh and mb):
            raise ConanException(
                "bitmap %s lacks %s_height define or %s_bits[] array" % (name, stem, stem))
        height = int(mh.group(1))
        nbytes = len(re.findall(r"0x[0-9a-fA-F]+", mb.group(1)))
        expected = ((width + 7) // 8) * height
        if nbytes != expected:
            raise ConanException(
                "bitmap %s: %d data bytes but %dx%d needs %d"
                % (name, nbytes, width, height, expected))

    def build(self):
        # Pure data package: nothing to compile.  Instead, validate every
        # bitmap the way a real consumer would parse it (X11 bitmap format:
        # width/height defines + packed byte array).
        apply_conandata_patches(self)
        names = self._bitmap_names()
        if len(names) != EXPECTED_COUNT:
            raise ConanException(
                "Makefile.am dist_bitmap_DATA lists %d files, expected %d"
                % (len(names), EXPECTED_COUNT))
        for name in names:
            self._validate_bitmap(name)
        self.output.info("xbitmaps: %d/%d bitmaps validated OK"
                         % (len(names), EXPECTED_COUNT))

    def package(self):
        names = self._bitmap_names()
        dest = os.path.join(self.package_folder, "include", "X11", "bitmaps")
        for name in names:
            copy(self, name, self.source_folder, dest)
        copy(self, "COPYING*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        installed = [f for f in os.listdir(dest) if os.path.isfile(os.path.join(dest, f))]
        if len(installed) != EXPECTED_COUNT:
            raise ConanException("installed %d bitmaps, expected %d"
                                 % (len(installed), EXPECTED_COUNT))

    def package_info(self):
        # Consumers do #include <X11/bitmaps/boxes> or read the files at
        # runtime from <pkg>/include/X11/bitmaps.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("pkg_config_name", "xbitmaps")
