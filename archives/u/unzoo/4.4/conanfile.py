#!/usr/bin/env python3
"""Conan recipe — unzoo 4.4 (extractor for zoo archives).

unzoo is Martin Schoenert's archive extractor for the ``.zoo`` format used by
Rahul Dhesi's ``zoo`` archiver.  It lists and extracts members (it cannot add
or delete them).  The file is in the Public Domain and the whole program is a
single C source file.

Build system : none.  The distribution is one C file whose header carries the
               build instruction — ``cc -o unzoo -DSYS_IS_UNIX -O unzoo.c``,
               optionally with ``-DSYS_HAS_MKDIR``.
Package form : a single CLI executable (``bin/unzoo``) — an application, so
               R38 requires a software-level commands.json.

Source note: the URL every downstream packager cites
(``archives.math.utk.edu/.../unzoo.c``) has been down since at least
2026-09-20.  The recipe therefore uses Debian's ``unzoo_4.4.orig.tar.gz``,
which is Debian's pristine-upstream tarball containing exactly one unzoo.c —
the same source, no Debian patches.  See conandata.yml and notes.md.

OHOS adaptation (patches/, see conandata.yml):

  * ``0001-unzoo-unix-portability.patch`` — the SYS_IS_UNIX branch calls
    ``strcpy``/``strcat``/``malloc``/``mkdir``/``utime``/``chmod`` but includes
    none of the headers declaring them; every call was an implicit declaration,
    which GCC 14+ treats as an error and C23 removed.  The same patch fixes
    ``SETF_TIME``, which passed an ``unsigned int[2]`` where POSIX
    ``utime()`` expects a ``struct utimbuf *`` — on LP64 (x86_64, aarch64/OHOS)
    ``time_t`` is 64-bit, so utime() read past the end of an 8-byte object.
  * ``0002-add-GNUmakefile.patch`` — adds the GNU make rule the distribution
    lacks, with the compiler and flags taken from the Conan toolchain
    environment rather than a hard-coded ``cc`` (R33).

Upstream tests: none — no test suite, no test data, no test target (see
test_package/MANIFEST.yml).  test_package therefore performs a real round
trip: it builds a spec-valid zoo archive with one stored member, lists it and
extracts it with the installed ``unzoo``, and compares the extracted bytes
with the original payload.  unzoo only prints "extracted" when the member's
CRC-16 matches, so that also proves the archive and CRC handling.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnzooConan(ConanFile):
    name = "unzoo"
    version = "4.4"
    description = "unzoo — extractor for zoo archives (Public Domain, ANSI C)"
    license = "Public Domain"
    # The original host (archives.math.utk.edu/.../unzoo.c) is dead; this is
    # the stable, authoritative page for the same pristine source.
    homepage = "https://sources.debian.org/src/unzoo/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "unzoo 4.4 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        # The Debian pristine-upstream tarball holds unzoo.c at its root — there
        # is no top-level directory, so strip_root would raise
        # "Can't untar a tgz containing files in the root with strip_root enabled".
        get(self, **self.conan_data["sources"])

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # NOTE: run make in the source folder (Autotools.make() would run it in
        # the build folder, where GNUmakefile is not).  The AutotoolsToolchain
        # environment is applied to self.run() either way.
        #
        # -j1 on purpose: this session shares the Harmony PC with a large
        # unrelated build and must not add parallel load.
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "unzoo", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
