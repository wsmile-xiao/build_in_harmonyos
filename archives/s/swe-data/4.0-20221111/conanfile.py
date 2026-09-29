#!/usr/bin/env python3
"""Conan recipe for swe-data 4.0-20221111 — Swiss Ephemeris ephemeris data files.

`swe-data` ships the **static data files** consumed by the Swiss Ephemeris
library (`libswe`, Astrodienst AG / Debian source package `libswe`): the binary
Chebyshev ephemeris files (`*.se1`, based on JPL DE431) plus the fixed-star /
asteroid-name / leap-second text tables. There is **no source code and no
compilation step** — the upstream tarball is a pure data payload.

Upstream layout of the tarball (four catalogues)::

    swe-basic-data/     sepl_18.se1 semo_18.se1 seas_18.se1 + 6 *.txt tables
    swe-standard-data/  51 *.se1   (sepl_/semo_/seas_ 8 each + seplm/semom/seasm 9 each)
    swe-extra-data/     96 *.se1   (sepl_/semo_/seas_ 19 each + seplm/semom/seasm 13 each)
    swe-sat-data/       32 sepm*.se1  (planetary moons and planet centre-of-body)

Debian installs the same payload **merged into one directory** with the moons in
a `sat/` sub-directory (debian/swe-*-data.install)::

    usr/share/libswe/ephe/*.se1
    usr/share/libswe/ephe/sat/sepm*.se1

and `libswe` resolves that directory either through `swe_set_ephe_path()` or
through the `SE_EPHE_PATH` environment variable. The recipe reproduces exactly
that layout, so a consumer only has to point `SE_EPHE_PATH` at
`<package_folder>/share/libswe/ephe` (`package_info()` also publishes the path
through `cpp_info.resdirs` and injects the variable into the Conan run
environment).

File-name convention (verified against the payload, see tests)::

    sepl_NN.se1    planets,      covers NN*100 .. NN*100+600 CE     (NN in 00..162)
    seplmNN.se1    planets,      covers -NN*100 .. -NN*100+600 CE   (NN in 06..132)
    semo_/semom    Moon (same indexing)
    seas_/seasm    main asteroids Chiron/Pholus/Ceres/Pallas/Juno/Vesta (same indexing)
    sepm<P><MM>    satellites; <P> = parent planet code, MM = 01..08 moon, 99 = COB

Measured span of this payload (from each file's header): 13000 BCE .. 16800 CE in
contiguous 600-year windows.  The `*132` triplet is shifted ~201 years against its
name (seplm132 wraps -12999..-12400 instead of -13200..-12600), which still leaves
the coverage gap-free because it overlaps the 126 files.

License: CC0-1.0 (the payload is considered public domain; Astrodienst granted
Debian the right to distribute it under CC0-1.0 — see `licenses/LICENSE`).
"""
import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# --- payload fingerprint (upstream swe-data 4.0-20221111, .orig.tar.gz, sha256 pinned in conandata.yml)
CATALOGS = ("swe-basic-data", "swe-standard-data", "swe-extra-data")
SATELLITE_CATALOG = "swe-sat-data"
EXPECTED_FILES_PER_CATALOG = {
    "swe-basic-data": 9,     # 3 *.se1 + 6 *.txt
    "swe-standard-data": 51,
    "swe-extra-data": 96,
    SATELLITE_CATALOG: 32,
}
EXPECTED_PAYLOAD_FILES = 188
EXPECTED_SE1_FILES = 182
EXPECTED_PAYLOAD_BYTES = 314404679
# sha256 over the sorted "<relative name> <size>\n" manifest of the 188 payload files
EXPECTED_PAYLOAD_DIGEST = "0a4fcc507e2dd1574e8e9c658d1fb5df2c305b638aff1b1a27dc119419f4938f"

LICENSE_TEXT = """\
Swiss Ephemeris ephemeris data files — swe-data 4.0-20221111
============================================================
SPDX-License-Identifier: CC0-1.0
Upstream: https://www.astro.com/swisseph   (Debian source package: swe-data)
Copyright: 1997-2023 Astrodienst AG, Switzerland

The binary data files distributed in this package (share/libswe/ephe/**) and the
text tables (seasnam.txt, seasnam2.txt, sefstars.txt, seorbelt.txt,
seleapsec.txt, sedeltat.txt.inactive) are, in the words of the Debian copyright
file for swe-data:

  "Though both the source code compressing and writing the binary data is
   copyrighted, and also the source code reading the data is copyrighted and
   published under the terms and conditions found on the Swiss Ephemeris website
   [https://www.astro.com/swisseph], the data in these Files can be considered to
   be in the Public Domain.

   These Files are based on the works of the Jet Propulsion Laboratory (JPL) of
   NASA [https://ssd.jpl.nasa.gov], which are also considered to be in the
   Public Domain [...]. Permission was granted to Astrodienst by Myles E.
   Standish [...] to include the JPL data files in the distribution of the Swiss
   Ephemeris [...]. Permission was granted by Astrodienst to package and
   distribute the Files under the CC0 1.0 Universal license [...]."

  "THE FILES ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE FILES OR THE USE OR OTHER DEALINGS IN THE
   FILES."

The complete CC0 1.0 Universal text is available at
https://creativecommons.org/publicdomain/zero/1.0/legalcode

Note: the Swiss Ephemeris *library* (libswe) that reads these files is a separate
work under AGPL-3.0-or-later / commercial dual licensing; this package only
carries the data.
"""

DOC_README = """\
swe-data 4.0-20221111 — Swiss Ephemeris static data files
=========================================================
Layout (identical to Debian's /usr/share/libswe/ephe):

  share/libswe/ephe/*.se1          planetary / Moon / main-asteroid ephemeris
  share/libswe/ephe/*.txt          fixed stars, asteroid names, leap seconds, ...
  share/libswe/ephe/sat/sepm*.se1  planetary moons + planet centre-of-body

Coverage of the delivered set (from the headers of every file, see the package's
consumer test): planets and Moon from 13000 BCE to 16800 CE in contiguous
600-year files; the basic catalogue covers 1800-2399 CE, the standard catalogue
already provides 5401 BCE to 5399 CE (the deepest files are the `*132` triplet,
whose windows are shifted ~201 years against their names).

How to use:
  export SE_EPHE_PATH=<prefix>/share/libswe/ephe
  libswe / swetest / any Swiss Ephemeris application will then find the data.
"""


class SweDataConan(ConanFile):
    name = "swe-data"
    version = "4.0-20221111"
    description = ("Swiss Ephemeris static data files (JPL DE431 based .se1 "
                   "ephemeris files for planets, Moon, main asteroids and "
                   "planetary moons, plus fixed-star/name/leap-second tables)")
    license = "CC0-1.0"
    homepage = "https://www.astro.com/swisseph"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Pure data package: no compilation, no libraries, no executables, and the
    # payload is architecture independent ("Architecture: all" in Debian).
    package_type = "unknown"

    _ephe_dir = os.path.join("share", "libswe", "ephe")
    _doc_dir = os.path.join("share", "doc", "swe-data")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ helpers
    def _manifest(self):
        """(relative name, size) of every payload file, moon files prefixed `sat/`."""
        entries = []
        for catalog in CATALOGS:
            catalog_dir = os.path.join(self.source_folder, catalog)
            if not os.path.isdir(catalog_dir):
                raise ConanException(f"catalogue directory missing in source: {catalog_dir}")
            names = sorted(os.listdir(catalog_dir))
            present = [n for n in names if os.path.isfile(os.path.join(catalog_dir, n))]
            if len(present) != EXPECTED_FILES_PER_CATALOG[catalog]:
                raise ConanException(
                    f"{catalog}: expected {EXPECTED_FILES_PER_CATALOG[catalog]} files, "
                    f"found {len(present)}")
            entries += [(n, os.path.getsize(os.path.join(catalog_dir, n))) for n in present]
        sat_dir = os.path.join(self.source_folder, SATELLITE_CATALOG)
        present = [n for n in sorted(os.listdir(sat_dir))
                   if os.path.isfile(os.path.join(sat_dir, n))]
        if len(present) != EXPECTED_FILES_PER_CATALOG[SATELLITE_CATALOG]:
            raise ConanException(
                f"{SATELLITE_CATALOG}: expected "
                f"{EXPECTED_FILES_PER_CATALOG[SATELLITE_CATALOG]} files, found {len(present)}")
        entries += [("sat/" + n, os.path.getsize(os.path.join(sat_dir, n))) for n in present]
        return entries

    def build(self):
        # No compilation. Verify the data payload itself: file count, total size
        # and a digest over the (name, size) manifest. A truncated download, a
        # different upstream revision or a silently missing catalogue fails here
        # instead of producing a data package that is quietly incomplete.
        entries = self._manifest()
        if len(entries) != EXPECTED_PAYLOAD_FILES:
            raise ConanException(
                f"payload has {len(entries)} files, expected {EXPECTED_PAYLOAD_FILES}")
        se1 = [n for n, _ in entries if n.endswith(".se1")]
        if len(se1) != EXPECTED_SE1_FILES:
            raise ConanException(
                f"payload has {len(se1)} *.se1 files, expected {EXPECTED_SE1_FILES}")
        total = sum(size for _, size in entries)
        if total != EXPECTED_PAYLOAD_BYTES:
            raise ConanException(
                f"payload is {total} bytes, expected {EXPECTED_PAYLOAD_BYTES}")
        digest = hashlib.sha256()
        for name, size in sorted(entries):
            digest.update(f"{name} {size}\n".encode("utf-8"))
        if digest.hexdigest() != EXPECTED_PAYLOAD_DIGEST:
            raise ConanException(
                f"payload manifest digest {digest.hexdigest()} does not match the "
                f"pinned upstream digest {EXPECTED_PAYLOAD_DIGEST}")
        empty = [n for n, size in entries if size == 0]
        if empty:
            raise ConanException(f"zero-length data files in payload: {empty}")

    def package(self):
        ephe = os.path.join(self.package_folder, self._ephe_dir)
        doc = os.path.join(self.package_folder, self._doc_dir)

        # Reproduce Debian's merged installation: all three flat catalogues land
        # in share/libswe/ephe/, the satellite catalogue in .../ephe/sat/.
        for catalog in CATALOGS:
            copy(self, "*", src=os.path.join(self.source_folder, catalog), dst=ephe)
        copy(self, "*", src=os.path.join(self.source_folder, SATELLITE_CATALOG),
             dst=os.path.join(ephe, "sat"))

        # The tarball's Makefile/README.txt are dangling symlinks into the Debian
        # packaging directory (debian/Makefile, debian/README.txt) which is *not*
        # part of the .orig tarball, so they carry no payload and are not shipped.
        os.makedirs(os.path.join(self.package_folder, "licenses"), exist_ok=True)
        os.makedirs(doc, exist_ok=True)
        for path in (os.path.join(self.package_folder, "licenses", "LICENSE"),
                     os.path.join(doc, "copyright")):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(LICENSE_TEXT)
        with open(os.path.join(doc, "README"), "w", encoding="utf-8") as handle:
            handle.write(DOC_README)

    def package_info(self):
        # The data root is the package's only interface: libswe looks for
        # <ephe>/sepl_*.se1|semo_*.se1|seas_*.se1 and <ephe>/sat/sepm*.se1.
        self.cpp_info.resdirs = [self._ephe_dir]
        # A data package installs no headers, libraries or executables; leaving the
        # defaults would make CMakeDeps emit phantom include/lib/bin paths.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Same contract as the Debian package: applications (swetest, libswe-based
        # code) find the data through SE_EPHE_PATH.
        self.runenv_info.define_path(
            "SE_EPHE_PATH", os.path.join(self.package_folder, self._ephe_dir))
