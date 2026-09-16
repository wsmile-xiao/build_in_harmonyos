#!/usr/bin/env python3
"""Conan recipe for d-shlibs 0.109 — Debian shared-library packaging helpers.

d-shlibs is a Debian-native package made of two pure bash scripts plus an
install-only Makefile. There is nothing to compile: upstream `make all' has an
empty recipe and `make install' merely copies the scripts into
$(DESTDIR)/usr/bin/ (verified by reading the shipped Makefile).

  * d-shlibmove   - moves a shared library file (plus the -dev symlink /
                    static / .la siblings) into the correct Debian package
                    directory and emits the matching debian/*.substvars
  * d-devlibdeps  - generates the `devlibs:Depends=' build-dependency line of
                    a -dev package from the DT_NEEDED entries of its libraries

Runtime commands used by the scripts (analysed from the shipped sources):
  d-shlibmove : dpkg-architecture, $DEB_HOST_GNU_TYPE-objdump, perl, sed,
                grep, awk, basename, dirname, readlink, mktemp, file
  d-devlibdeps: dpkg-architecture, $DEB_HOST_GNU_TYPE-objdump, apt-cache, apt

Upstream tests (R51 inventory, see notes.md and test_package/MANIFEST.yml):
  `make check'      = `bash -n' x2 + `shellcheck' x2
  `make test-build' = apt-get source + debuild of 4 sample packages
  debian/tests/     = one active autopkgtest (uppercase.d) driving d-shlibmove
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, download,
                               export_conandata_patches)


class DshlibsConan(ConanFile):
    name = "d-shlibs"
    version = "0.109"
    package_type = "application"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/d-shlibs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = ("d-shlibs — Debian shared library package building helper "
                   "scripts (d-shlibmove + d-devlibdeps, pure bash, no compile)")

    settings = "os", "compiler", "build_type", "arch"

    # Pure scripts: nothing is compiled and no library is produced, but the
    # tools the scripts wrap live in the Debian toolchain packages, which are
    # therefore declared as requirements.
    #   dpkg      -> dpkg-architecture (both scripts run `eval $(dpkg-architecture -s)')
    #   binutils  -> $DEB_HOST_GNU_TYPE-objdump (-p for SONAME / NEEDED)
    #   debhelper -> the Debian source package Build-Depends on
    #                debhelper-compat (= 13); kept for family consistency
    #
    # `apt' is deliberately NOT declared: the Debian Depends field lists it and
    # d-devlibdeps calls apt-cache/apt, but apt is not published on the ohpcd
    # remote (W0 evidence recorded in manifest.yaml -> dependencies_unavailable).
    # `shellcheck' is NOT declared either: only upstream `make check' needs it
    # and it is likewise not published.
    requires = "debhelper/13.3.4", "dpkg/1.23.7", "binutils/2.46.0"

    def export_sources(self):
        # No upstream patch is needed for this package (conandata.yml declares
        # no `patches` entry, so both calls below are no-ops); the standard
        # scaffolding is kept so a future portability fix has a home.
        export_conandata_patches(self)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "d-shlibs-debian-0.109.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # Sandbox `get()' can raise PermissionError -> download + manual
        # extraction. The salsa git-archive is rooted at
        # `d-shlibs-debian-0.109/', so it is flattened into the source folder
        # (hidden files included). `--no-same-owner' tolerates ownership errors.
        self.run("tar -xzf d-shlibs-debian-0.109.tar.gz --no-same-owner || true")
        self.run("cp -a d-shlibs-debian-0.109/. . && rm -rf d-shlibs-debian-0.109")

    def build(self):
        # No-op by design: upstream `make all' is an empty rule. The scripts
        # need no code generation and no upstream patch is applied.
        apply_conandata_patches(self)

    def package(self):
        # Pick files explicitly (never copy the whole tree):
        #   d-shlibmove / d-devlibdeps -> <pkg>/bin/            (0755)
        #   d-shlibmove.1 / d-devlibdeps.1 -> <pkg>/share/man/man1/
        #   COPYING -> <pkg>/licenses/
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        licdir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        os.makedirs(licdir, exist_ok=True)
        for script in ("d-shlibmove", "d-devlibdeps"):
            dst = os.path.join(bindir, script)
            shutil.copy(os.path.join(self.source_folder, script), dst)
            os.chmod(dst, 0o755)
        for man in ("d-shlibmove.1", "d-devlibdeps.1"):
            shutil.copy(os.path.join(self.source_folder, man),
                        os.path.join(mandir, man))
        shutil.copy(os.path.join(self.source_folder, "COPYING"),
                    os.path.join(licdir, "COPYING"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
