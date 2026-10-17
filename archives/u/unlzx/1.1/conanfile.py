#!/usr/bin/env python3
"""Conan recipe — unlzx 1.1 (extractor for Amiga LZX archives).

unlzx is Erik Meusel's portable ANSI-C unpacker for the Amiga LZX archive
format (the only way to read `.lzx` archives on a POSIX system).  It is
distributed through Aminet as a single gzip-compressed C file; v1.1 added the
ability to read an archive from stdin.

Build system : none.  The distribution is one C file plus a readme; the only
               build instruction is the comment at the top of the source —
               ``/* Compile with: gcc unlzx.c -ounlzx -O6 */``.
Package form : a single CLI executable (``bin/unlzx``) — an application, so
               R38 requires a software-level commands.json.

OHOS adaptation (patches/, see conandata.yml):

  * ``0001-unlzx-missing-includes.patch`` — the source calls ``mkdir()`` and
    ``getopt()`` but includes neither ``<sys/stat.h>`` nor ``<unistd.h>``.  Both
    were implicit declarations; GCC 14+ (and C23) make that a hard error, so
    the package would not compile on a modern toolchain at all.
  * ``0002-add-GNUmakefile.patch`` — adds the GNU make rule the distribution
    lacks, with the compiler and flags taken from the Conan toolchain
    environment rather than a hard-coded ``gcc`` (R33).

Upstream tests: none — there is no test suite, no test data and no test
target of any kind (see test_package/MANIFEST.yml).  The verification this
package does provide is a real round trip: test_package builds a spec-valid
LZX archive containing a stored member, has the installed ``unlzx`` extract
it, and compares the extracted bytes with the original payload.  That
exercises the info-header check, the archive-header CRC, the per-file data
CRC and the extraction path.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnlzxConan(ConanFile):
    name = "unlzx"
    version = "1.1"
    description = ("unlzx — extractor for Amiga LZX archives "
                   "(portable ANSI C implementation)")
    # The upstream distribution carries NO licence statement — neither
    # unlzx.c nor the Aminet readme mentions copyright, licence or
    # redistribution terms.  Declared honestly as unknown rather than
    # guessed; see notes.md §1.
    license = "unknown"
    homepage = "https://aminet.net/package/misc/unix/unlzx.c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "unlzx 1.1 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        # conan's get() decompresses a bare .gz: unlzx.c.gz -> unlzx.c
        get(self, **self.conan_data["sources"])

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # NOTE: Autotools.make() runs make in the *build* folder, which is not
        # where the sources are (basic_layout keeps them apart).  Run it in the
        # source folder instead; the AutotoolsToolchain environment — CC from
        # tools.build:compiler_executables plus CFLAGS/CPPFLAGS/LDFLAGS — is
        # applied to self.run() either way.
        #
        # -j1 on purpose: this session shares the Harmony PC with a large
        # unrelated build and must not add parallel load.
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "unlzx", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
