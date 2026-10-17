#!/usr/bin/env python3
"""Conan recipe for libyubikey, Yubico's low-level YubiKey OTP C library."""
import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibyubikeyConan(ConanFile):
    name = "libyubikey"
    version = "1.13"
    description = "C library for manipulating Yubico one-time passwords (modhex, CRC16, AES-128, OTP parse/generate)"
    license = "BSD-2-Clause"
    homepage = "https://developers.yubico.com/yubico-c/"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libyubikey is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def _patch_configure_mktemp(self, configure_path):
        # HMDFS fix (same as abnfgen/anubis): autotools' config.status creates
        # its private temp dir via `(umask 077 && mktemp -d "./confXXXXXX")`;
        # on HarmonyOS the resulting setgid dir (drwx--S---) is not writable
        # and config.status dies with "could not setup config files machinery".
        # configure embeds this snippet verbatim into config.status, so the
        # replacement must happen in configure itself before it is invoked.
        contents = load(self, configure_path)
        old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"'
        new = 'tmp=./conf$$-$RANDOM && mkdir "$tmp"'
        if old in contents:
            save(self, configure_path, contents.replace(old, new))
        else:
            self.output.warn("OHOS mktemp patch: pattern not found in configure "
                             "(upstream text may have changed); build may fail on hmdfs")

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            # HMDFS denies execve() of freshly extracted scripts (chmod is
            # masked to 750 under a foreign owner), while ELF binaries and
            # interpreter-mediated scripts run fine.  Invoke configure through
            # /bin/sh explicitly — same approach as the anubis recipe.
            os.environ["CONFIG_SHELL"] = "/bin/sh"
            os.environ["SHELL"] = "/bin/sh"
            os.environ.setdefault("TMPDIR", os.path.expanduser("~/tmp"))
            os.makedirs(os.environ["TMPDIR"], exist_ok=True)
            # The conanbuild PATH does not include the hnp tool directory
            # (CC is referenced by absolute path there), so configure cannot
            # find `ar`/`ranlib` and falls back to a bogus "link -lib"
            # archiver probe.  ar/ranlib/ld live in the hnp bin dir.
            _hnp_bin = "/data/service/hnp/bin"
            if os.path.isdir(_hnp_bin):
                os.environ["PATH"] = _hnp_bin + os.pathsep + os.environ.get("PATH", "")
            self._patch_configure_mktemp(os.path.join(self.source_folder, "configure"))

        args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--enable-static" if not self.options.shared else "--disable-static",
            "--disable-shared" if not self.options.shared else "--enable-shared",
            # a2x (asciidoc) only regenerates man pages in maintainer mode;
            # the tarball ships pre-built man pages.
            "A2X=true",
        ]
        self.run(
            "sh ./configure %s" % " ".join(shlex.quote(a) for a in args),
            env="conanbuild",
            cwd=self.source_folder,
        )
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)
        # Upstream regression suite: tests/selftest covers modhex/hex codec,
        # AES-128 block ops, OTP generate/parse roundtrip and CRC16 vectors.
        self.run("make check -j1", env="conanbuild", cwd=self.source_folder)

    def package(self):
        self.run(
            "make -j1 install DESTDIR=%s" % shlex.quote(self.package_folder),
            env="conanbuild",
            cwd=self.source_folder,
        )
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Conan 2 copy() has no delete= argument; drop libtool *.la wrappers manually.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["yubikey"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
