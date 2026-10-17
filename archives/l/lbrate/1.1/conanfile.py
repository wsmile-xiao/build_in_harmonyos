#!/usr/bin/env python3
"""Conan recipe — lbrate 1.1 (extract/decompress CP/M LBR archives).

lbrate (Russell Marks, 2001, GPL-2.0-or-later) lists, tests and extracts CP/M
``.lbr`` archives and transparently decompresses their squeezed (``?Q?``),
crunched (``?Z?``) and LZH (``?Y?``) members.  Five ANSI C files, no deps.

Build system : a plain upstream Makefile (``CC=gcc`` / ``CFLAGS=-O2 -Wall``
               hard-coded, no configure).  Command-line make variables
               override makefile assignments, so the recipe passes the Conan
               profile compiler as ``CC=`` — no patch is needed (R33: the
               compiler comes from ``tools.build:compiler_executables``, not
               from a shell variable).  Upstream ``make install`` is not used
               because it installs into ``/usr/local``; package() copies the
               two artifacts instead.
Package form : one CLI executable (``bin/lbrate``) plus its man page, so R38
               requires the software-level commands.json.
"""
import os
import shlex
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, check_sha256, copy,
                               export_conandata_patches, get, unzip)
from conan.tools.layout import basic_layout


class LbrateConan(ConanFile):
    name = "lbrate"
    version = "1.1"
    description = "Extract/decompress CP/M LBR archives (squeezed, crunched and LZH members)"
    license = "GPL-2.0-or-later"
    homepage = "https://ibiblio.org/pub/Linux/utils/compress/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cpm", "lbr", "archive", "decompression")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("lbrate 1.1 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        data = self.conan_data["sources"][self.version]
        try:
            get(self, **data, strip_root=True)
            return
        except ConanException as exc:
            # ibiblio answers .tar.gz with a Content-Encoding header, so the bytes
            # on disk depend on the client: curl (and the CI pre-download, which
            # rewrites the URL to file://) keeps the published gzip whose sha256
            # is recorded in conandata.yml, whereas conan's requests downloader
            # transparently gunzips it into a bare tar -> sha256 mismatch.
            # urllib neither requests nor decodes a content encoding, so it lands
            # the published bytes; check_sha256 still guards integrity.
            self.output.warning("conan download of the upstream tarball failed ({}); "
                                "retrying with urllib to keep the published bytes".format(exc))
        archive = os.path.join(self.source_folder, "lbrate-1.1.tar.gz")
        with urllib.request.urlopen(data["url"], timeout=120) as resp:
            payload = resp.read()
        with open(archive, "wb") as handler:
            handler.write(payload)
        check_sha256(self, archive, data["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def build(self):
        apply_conandata_patches(self)  # no patches for 1.1; kept for the standard recipe shape
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # CFLAGS keeps the upstream "-O2 -Wall"; -j1 because the sources are tiny.
        self.run("make -j1 lbrate CC={}".format(shlex.quote(cc)), cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "lbrate", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "lbrate.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
