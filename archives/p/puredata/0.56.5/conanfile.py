#!/usr/bin/env python3
"""Conan recipe — puredata 0.56.5 (autotools, application).

Pd (Pure Data) is a real-time graphical programming environment for
audio/video processing. Build system: autotools (needs autoreconf — the
upstream tarball ships only configure.ac, no generated configure).

OHOS notes (see notes.md):
- config.status's embedded `mktemp -d "./confXXXXXX"` fails on HMDFS
  (shell redirect into the mktemp dir is denied); work around by exporting
  TMPDIR pointing at a plain directory in the build folder.
- Upstream tarball has no generated configure: run `autoreconf -fi`.
- The CI worker ships autoconf 2.72 but no automake/libtool (E178) while a
  developer machine normally has the whole autotools stack on PATH, so only the
  tools the build host is actually missing become tool_requires.
- ALSA is unavailable: configure with `--disable-alsa` (patch 0001 keeps the ALSA hostapi source out of
  libportaudio when the Automake ALSA condition is disabled.
- musl libc has no pthread_cancel though PTHREAD_CANCELED is defined in
  the sysroot headers (patch 0002 forces the no-cancel fallback path).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PuredataConan(ConanFile):
    name = "puredata"
    version = "0.56.5"
    description = "Pure Data (Pd) real-time graphical programming environment for audio"
    license = "BSD-3-Clause"
    homepage = "https://puredata.info"
    url = "https://github.com/pure-data/pure-data"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "patch-autotools-ohos.pl",
            src=os.path.join(self.recipe_folder, "patches"),
            dst=os.path.join(self.export_sources_folder, "patches"),
        )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"puredata supports Linux/OHOS only, got {self.settings.os}"
            )

    # Bootstrap tools this recipe may need, and the program that proves the host
    # already has one. autoconf/m4 are deliberately absent: the CI worker ships
    # autoconf 2.72 (which needs m4 at run time), and the registry's m4/autoconf
    # binaries live on another recipe revision than the one this profile resolves
    # (m4#1727f439 -> 579a4b17…, autoconf#e2324a34 -> 8c781e33…), so
    # `--build=missing` would compile them from source and watch their *own*
    # config.guess(2021-05-24) fail writing dummy.c on HMDFS ("cannot guess build
    # type", E114/E136 class) - outside anything this recipe controls.
    _BOOTSTRAP_TOOLS = (
        ("automake/1.18", "automake", "share/automake-1.18"),
        ("libtool/2.5.4", "libtoolize", None),
    )

    def build_requirements(self):
        # E178: a bare `autoreconf -fi` on the CI worker dies with
        # `Can't exec "aclocal"`; on a dev machine the host already provides it.
        for ref, probe, _share in self._BOOTSTRAP_TOOLS:
            if not shutil.which(probe):
                self.tool_requires(ref)

    def _bootstrap_env(self):
        """PATH/PERL5LIB for autoreconf under whichever autotools are in use.

        Only the tool_requires that were actually resolved contribute paths; the
        rest comes from the host PATH. The automake wrappers shebang the *system*
        perl, so PERL5LIB may only name automake's pure-Perl module dir - adding
        the conan perl's XS libs there breaks them (dual-perl ABI trap).
        """
        path_prefix = []
        perl5lib = []
        for ref, _probe, share in self._BOOTSTRAP_TOOLS:
            try:
                dep = self.dependencies.build[ref]
            except KeyError:
                continue
            path_prefix.extend(
                os.path.join(dep.package_folder, d) for d in dep.cpp_info.bindirs
            )
            if share:
                d = os.path.join(dep.package_folder, share)
                if not os.path.isdir(d):
                    raise ConanInvalidConfiguration(
                        "autotools share dir not found: %s" % d)
                perl5lib.append(d)
        return ":".join(path_prefix), ":".join(perl5lib)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, filename="puredata-0.56.5.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: never rely on undefined shell env — use conanbuild env only.
        # HMDFS workaround (notes.md #1): config.status must mktemp under a
        # plain TMPDIR inside the build folder, not under the source dir.
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        path_prefix, perl5lib = self._bootstrap_env()
        self.run(
            'PATH="%s:$PATH" PERL=perl PERL5LIB="%s" '
            'TMPDIR="%s" TMP="%s" TEMP="%s" autoreconf -fi'
            % (path_prefix, perl5lib, tmpdir, tmpdir, tmpdir),
            env="conanbuild",
            cwd=self.source_folder,
        )
        # Teach the bundled GNU config helpers to identify HarmonyOS; do not
        # bypass their detection with --build/--host flags (E205).
        self.run(
            'perl "%s" m4/config/config.guess m4/config/config.sub'
            % os.path.join(self.export_sources_folder, "patches", "patch-autotools-ohos.pl"),
            env="conanbuild",
            cwd=self.source_folder,
        )
        # HMDFS workaround (notes.md #1 / E528-style, same fix as acl/2.3.2):
        # config.status mktemps a 0700 (umask 077) dir, and the subsequent
        # shell redirect creating subs*.awk inside it is denied on HMDFS.
        # Relax to umask 000 in the generated configure (config.status
        # inherits the same block from it).
        self.run(
            r"""sed -i 's|umask 077 && mktemp -d "\./confXXXXXX"|umask 000 \&\& mktemp -d "./confXXXXXX"|; s|umask 077 && mkdir "\$tmp"|umask 000 \&\& mkdir "$tmp"|' configure""",
            env="conanbuild",
            cwd=self.source_folder,
        )
        autotools = Autotools(self)
        autotools.configure(args=["--prefix=/", "--disable-alsa"])
        autotools.make(args=["-j1"])
        # No Makefile.am registers TESTS/check_PROGRAMS (see
        # test_package/MANIFEST.yml), so this runs zero cases; it is executed
        # anyway to prove that instead of asserting it. test_package supplies the
        # executable consumer and OHOS ABI checks.
        autotools.make(target="check")

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
