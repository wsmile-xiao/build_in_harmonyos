#!/usr/bin/env python3
"""Conan recipe — ppunpack 1.0 (PowerPacker decruncher, Aminet "ppsmall").

ppunpack is Marc Espie's small portable C decruncher for Amiga PowerPacker
("PP20") data files.  It is distributed on Aminet as ppsmall-1.0.tar.Z:
README, a 25-line Makefile, depack.c/depack.h and ppunpack.c.

Build system : a hand-written Makefile.  It hard-codes ``CC=acc`` and its
               default target is ``all: ppunpack check``, where ``check``
               unpacks ``sf.pp`` and diffs it against ``sf.chk`` — two sample
               files that exist only in the long ppunpack-1.0.tar.Z, not in
               this short distribution.  Both are handled from the make
               command line (explicit ``ppunpack`` target, ``CC``/``COPTS``
               overrides); no source file is patched.
Source format: Unix compress(1) ``.tar.Z``.  conan's get()/unzip() only know
               zip/gz/bz2/xz, and the device userland (toybox gzip) has no LZW
               decoder, so source() downloads the archive with its sha256 and
               decodes it with the small LZW reader below.
Linking      : ``-static-pie``.  The program uses nothing but libc; linking it
               statically keeps the PIE/RELRO hardening, removes the runtime
               dependency on the musl loader, and lets the delivered binary
               itself be executed by test_package under qemu-aarch64 on x86
               runners (see notes.md).
Package form : one CLI executable, ``bin/ppunpack`` — an application, so R38
               requires the software-level commands.json.
"""
import io
import os
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches)
from conan.tools.layout import basic_layout


def _unlzw(data):
    """Decode a Unix compress(1) stream (.Z); port of gzip's unlzw()."""
    if len(data) < 3 or data[:2] != b"\x1f\x9d":
        raise ConanException("ppsmall-1.0.tar.Z: not a compress(1) stream")
    maxbits = data[2] & 0x1F
    block_mode = bool(data[2] & 0x80)
    if not 9 <= maxbits <= 16:
        raise ConanException("ppsmall-1.0.tar.Z: bad max code width %d" % maxbits)
    maxmaxcode = 1 << maxbits
    total_bits = len(data) * 8
    pos = group = 24          # bit position / start of current code-width group
    n_bits = 9
    maxcode = (1 << n_bits) - 1
    table = [bytes([i]) for i in range(256)] + [b""]   # 256 = CLEAR
    free_ent = 257 if block_mode else 256
    out = bytearray()
    old = None
    while True:
        if free_ent > maxcode and n_bits < maxbits:
            # a width change skips to the end of the current 8-code group
            span = n_bits * 8
            pos = group = group + -(-(pos - group) // span) * span
            n_bits += 1
            maxcode = maxmaxcode if n_bits == maxbits else (1 << n_bits) - 1
            continue
        if pos + n_bits > total_bits:
            break
        byte, bit = divmod(pos, 8)
        code = (int.from_bytes(data[byte:byte + 3], "little") >> bit) & ((1 << n_bits) - 1)
        pos += n_bits
        if old is None:
            if code >= 256:
                raise ConanException("ppsmall-1.0.tar.Z: corrupt first code")
            out += table[code]
            old = code
            continue
        if code == 256 and block_mode:
            span = n_bits * 8
            pos = group = group + -(-(pos - group) // span) * span
            del table[257:]
            free_ent = 256
            n_bits = 9
            maxcode = (1 << n_bits) - 1
            continue
        if code < len(table):
            entry = table[code]
        elif code == free_ent:
            entry = table[old] + table[old][:1]
        else:
            raise ConanException("ppsmall-1.0.tar.Z: corrupt code %d" % code)
        out += entry
        if free_ent < maxmaxcode:
            new = table[old] + entry[:1]
            if free_ent < len(table):
                table[free_ent] = new
            else:
                table.append(new)
            free_ent += 1
        old = code
    return bytes(out)


class PpunpackConan(ConanFile):
    name = "ppunpack"
    version = "1.0"
    description = "ppunpack - portable decruncher for Amiga PowerPacker (PP20) data files"
    # README: "copyright (c) Marc Espie, 1995 ... loosely based on the original
    # powerpacker decruncher code, copyright (c) Nico Francois.  THIS
    # SOURCE-CODE CAN BE USED FOR NON COMMERCIAL PURPOSES ONLY, IN PPDECRUNCH
    # OR TRACKER.  PLEASE CONTACT Nico Francois ... FOR ANY OTHER USES."
    # No SPDX id exists for these terms; the README is shipped as
    # licenses/README.
    license = "LicenseRef-ppunpack-noncommercial"
    homepage = "https://aminet.net/package/misc/unix/ppsmall-1.0"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("amiga", "powerpacker", "decompression", "cli")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ppunpack 1.0 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"][self.version]
        archive = os.path.join(self.source_folder, "ppsmall-1.0.tar.Z")
        download(self, src["url"], archive, sha256=src["sha256"])
        with open(archive, "rb") as handle:
            tar_bytes = _unlzw(handle.read())
        os.remove(archive)
        # Members are PPUnpack/<file>; strip that top directory and accept
        # plain relative names only.
        with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
            for member in tar.getmembers():
                parts = member.name.split("/", 1)
                if len(parts) != 2 or not parts[1] or not member.isfile():
                    continue
                rel = parts[1]
                if rel.startswith("/") or ".." in rel.split("/"):
                    raise ConanException("unsafe member in archive: %s" % member.name)
                dest = os.path.join(self.source_folder, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as handle:
                    handle.write(tar.extractfile(member).read())

    def build(self):
        apply_conandata_patches(self)   # no patches today; kept for the convention
        compilers = self.conf.get("tools.build:compiler_executables",
                                  check_type=dict, default={})
        cc = compilers.get("c", "cc")
        # Command-line CC/COPTS override the Makefile's "CC=acc"; building the
        # "ppunpack" target skips "check" (its sf.pp/sf.chk are not in this
        # distribution; test_package runs that check against the installed
        # binary).  COPTS feeds both the compile rule and the link rule:
        # upstream's -O3, -fPIE for the objects, -static-pie for the link.
        self.run("make -j1 ppunpack CC='%s' COPTS='-O3 -fPIE -static-pie'" % cc,
                 env="conanbuild", cwd=self.source_folder)

    def package(self):
        copy(self, "ppunpack", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
