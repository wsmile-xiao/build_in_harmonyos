#!/usr/bin/env python3
"""Conan recipe — puredata 0.54.1 (autotools, application).

Pd (Pure Data) is a real-time graphical programming environment for
audio/video processing. Build system: autotools (needs autoreconf — the
upstream tarball ships only configure.ac, no generated configure).

OHOS notes (see notes.md):
- config.status's embedded `mktemp -d "./confXXXXXX"` fails on HMDFS
  (shell redirect into the mktemp dir is denied); work around by exporting
  TMPDIR pointing at a plain directory in the build folder.
- Upstream tarball has no generated configure: run `autoreconf -fi`.
- ALSA is unavailable: configure with --without-alsa (patch 0001 keeps the
  ALSA hostapi source out of libportaudio when ALSA is disabled).
- musl libc has no pthread_cancel though PTHREAD_CANCELED is defined in
  the sysroot headers (patch 0002 forces the no-cancel fallback path).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools
from conan.tools.layout import basic_layout


class PuredataConan(ConanFile):
    name = "puredata"
    version = "0.54.1"
    description = "Pure Data (Pd) real-time graphical programming environment for audio"
    license = "BSD-3-Clause"
    homepage = "https://puredata.info"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"puredata supports Linux/OHOS only, got {self.settings.os}"
            )

    def build_requirements(self):
        # CI worker #54497: worker ships autoconf 2.72 but NO automake ->
        # `Can't exec "aclocal"` in autoreconf. Same E178 pattern as
        # apertium/3.9.12, bwm-ng, zbar: pull the bootstrap toolchain via
        # tool_requires. configure.ac uses AM_INIT_AUTOMAKE + AC_PROG_LIBTOOL,
        # so libtool is needed too.
        self.tool_requires("m4/1.4.19")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: never rely on undefined shell env — use conanbuild env only.
        # HMDFS workaround (notes.md #1): config.status must mktemp under a
        # plain TMPDIR inside the build folder, not under the source dir.
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = f"TMPDIR={tmpdir}"
        # Bootstrap under the tool_requires'd autotools (E178 pattern from
        # apertium/3.9.12): PATH-prefix m4/autoconf/automake/libtool bindirs,
        # collapse PERL5LIB to the pure-Perl module dirs of automake/autoconf
        # (the automake wrappers shebang the SYSTEM perl; a conanbuild
        # PERL5LIB pointing at conan perl's XS libs breaks it), and point
        # TMPDIR at a writable build-local dir (OHOS /tmp is read-only).
        path_prefix = []
        perl5lib = []
        for ref, share in (
            ("m4/1.4.19", None),
            ("autoconf/2.72", "share/autoconf"),
            ("automake/1.18", "share/automake-1.18"),
            ("libtool/2.5.4", None),
        ):
            dep = self.dependencies.build[ref]
            path_prefix.extend(dep.cpp_info.bindirs)
            if share:
                d = os.path.join(dep.package_folder, share)
                if not os.path.isdir(d):
                    raise ConanInvalidConfiguration(
                        "autotools share dir not found: %s" % d)
                perl5lib.append(d)
        self.run(
            'PATH="%s:$PATH" PERL=perl PERL5LIB="%s" TMPDIR="%s" TMP="%s" TEMP="%s" autoreconf -fi'
            % (":".join(path_prefix), ":".join(perl5lib),
               tmpdir, tmpdir, tmpdir),
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
        # CI #56266: config.guess fails on OHOS twice — it cannot map
        # uname -s "HarmonyOS" / "HongMeng Kernel" to a triplet, and its
        # compiler probe (`dummy.c`) hits "Permission denied" when written
        # under the HMDFS TMPDIR (E114-style). Pass the triplet explicitly
        # so configure never runs the config.guess probe; same mature
        # approach as argp-standalone / abiword-plugin-* / a52dec.
        self.run("./configure --prefix=/ --without-alsa "
                 "--build=aarch64-unknown-linux-ohos "
                 "--host=aarch64-unknown-linux-ohos",
                 env="conanbuild",
                 cwd=self.source_folder,)
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)
        # Upstream has no registered tests (see test_package/MANIFEST.yml);
        # keep `make check` to prove the check target stays green.
        self.run("make check", env="conanbuild", cwd=self.source_folder)

    def package(self):
        self.run(
            f"make install DESTDIR={self.package_folder}",
            env="conanbuild",
            cwd=self.source_folder,
        )
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
