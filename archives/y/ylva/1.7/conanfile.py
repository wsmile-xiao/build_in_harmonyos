#!/usr/bin/env python3
"""Conan recipe for ylva 1.7 — command-line password manager.

Ylva stores entries (title / user / url / password / notes) in an SQLite
database that lives behind a pointer file ``$HOME/.ylva.open_db``.  From the
shell it can initialise, list, copy, edit and delete entries, search them with
``LIKE`` or POSIX regular expressions, generate random passwords, render an
entry as a terminal QR code, and encrypt/decrypt the whole database with
AES-256-CTR keyed by PBKDF2-HMAC-SHA256 (200 000 iterations, 64-byte salt)
and authenticated with HMAC-SHA512.  The program is C11 and POSIX-only.

Upstream build system: a hand-written ``src/Makefile``, no configure step and
no ``check``/``test`` target.  ``make`` compiles every ``src/*.c`` and links

    -lcrypto -lsqlite3 -lqrcodegen -lrt

``build()`` therefore drives that Makefile with command-line variable
injections instead of patching it:

    CC      from Conan conf ``tools.build:compiler_executables`` (R33 — never a
            bare shell ``${CC}``, which is empty on release workers and would
            silently produce a host build)
    CFLAGS  ``-O2 -std=c11 -Wall`` plus the dependency include dirs.  Upstream
            defaults CFLAGS to ``-g``, so the default has to be replaced, not
            appended to — the ``-std=c11 -Wall`` upstream adds itself is
            repeated here for that reason.
    LDFLAGS the dependency ``-L`` directories
    LIBS    upstream's list, kept verbatim.  ``-lrt`` is a no-op on OHOS: musl
            (and hence the OHOS libc) ships an empty ``librt.a`` compatibility
            shim, and the timer/clock entry points live in libc itself.

HarmonyOS PC (aarch64) adaptation:
    * openssl, sqlite3 and libqrcodegen are all consumed in their static
      variants (each of those recipes is built ``shared=False``), so the
      packaged binary's ``DT_NEEDED`` carries ``libc.so`` only — no
      system-name library is dropped into the OHOS ``/lib`` (R26).
    * ``src/qr.c`` includes ``<qrcodegen/qrcodegen.h>`` — the layout Debian's
      ``libqrcodegen-dev`` installs — while the C library packaged by this
      ecosystem installs the header flat as ``include/qrcodegen.h``.  Rather
      than patching upstream, ``build()`` generates a one-line forwarding
      header in a build-only include tree, so ylva's own sources stay
      byte-identical to the release tarball.
    * No source patch at all: ylva never raises privileges, never writes to
      ``/tmp`` (its state lives under ``$HOME``), and uses only POSIX
      interfaces the OHOS musl libc provides.

Artifacts: ``bin/ylva`` and ``share/man/man1/ylva.1`` (the software-level
``commands.json`` declares the CLI, R38).
License: MIT.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class YlvaConan(ConanFile):
    name = "ylva"
    version = "1.7"
    description = (
        "Command-line password manager: SQLite-backed entry store with "
        "AES-256-CTR + PBKDF2/HMAC-SHA512 whole-database encryption, "
        "LIKE and regex search, password generation and terminal QR codes"
    )
    license = "MIT"
    homepage = "https://github.com/nrosvall/ylva"
    url = "https://github.com/nrosvall/ylva"
    topics = ("password-manager", "cli", "sqlite", "openssl", "qr-code",
              "security")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)
        # Hand-written Makefile project: build in the source folder so the
        # object files and the `ylva` binary land next to the sources, exactly
        # where upstream's src/Makefile puts them.
        self.folders.build = "."

    def export_sources(self):
        # No patches ship with this recipe; kept so the export layout follows the
        # repository convention and stays correct if an adaptation patch is ever
        # added to conandata.yml.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # crypto.c    -> <openssl/evp.h>, <openssl/hmac.h>          (-lcrypto)
        # pwd-gen.c   -> <openssl/err.h>, <openssl/rand.h>          (RAND_bytes)
        # db.c        -> <sqlite3.h>                                (-lsqlite3)
        # qr.c        -> <qrcodegen/qrcodegen.h>                    (-lqrcodegen)
        self.requires("openssl/3.5.8.1")
        self.requires("sqlite3/3.49.1")
        self.requires("libqrcodegen/1.8.0")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                "ylva requires a POSIX host (Linux or OHOS): it uses termios, "
                "getline, /dev/urandom and <sys/stat.h>")

    @staticmethod
    def _dep_dir(dep, attr):
        """First cpp_info directory of a dependency, made absolute."""
        dirs = list(getattr(dep.cpp_info, attr, []) or [])
        if not dirs:
            return ""
        path = dirs[0]
        return path if os.path.isabs(path) else os.path.join(dep.package_folder, path)

    def generate(self):
        def dirs(name):
            dep = self.dependencies[name]
            inc = self._dep_dir(dep, "includedirs")
            lib = self._dep_dir(dep, "libdirs")
            if not inc or not lib:
                raise ConanException(
                    "%s package exposes no include/lib dirs — cannot link ylva"
                    % name)
            return inc, lib

        self._ossl_inc, self._ossl_lib = dirs("openssl")
        self._sql_inc, self._sql_lib = dirs("sqlite3")
        self._qr_inc, self._qr_lib = dirs("libqrcodegen")

    @property
    def _src_dir(self):
        return os.path.join(self.source_folder, "src")

    def build(self):
        # conandata.yml currently declares no patches, so this is a no-op; it stays
        # in place so the adaptation path is wired up if a patch is ever needed.
        apply_conandata_patches(self)

        # R33: compiler path from Conan conf, never from an undefined shell var.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # qr.c asks for <qrcodegen/qrcodegen.h>; this ecosystem's
        # libqrcodegen/1.8.0 installs the C header flat.  Reproduce the
        # conventional install layout with a one-line forwarding header in a
        # build-only include tree — upstream sources stay untouched.
        compat = os.path.join(self.build_folder, "_qrcodegen_compat")
        save(self, os.path.join(compat, "qrcodegen", "qrcodegen.h"),
             "#include <qrcodegen.h>\n")

        cflags = " ".join([
            "-O2", "-std=c11", "-Wall",
            "-I%s" % compat,
            "-I%s" % self._qr_inc,
            "-I%s" % self._ossl_inc,
            "-I%s" % self._sql_inc,
        ])
        ldflags = " ".join([
            "-L%s" % self._qr_lib,
            "-L%s" % self._ossl_lib,
            "-L%s" % self._sql_lib,
        ])
        # R9: -j1.  GNU make gives command-line assignments precedence over
        # makefile ones, so this single invocation replaces CC/CFLAGS/LDFLAGS
        # and keeps upstream's LIBS list (including its librt shim) intact.
        self.run(
            'make -C "{src}" -j1 CC="{cc}" CFLAGS="{cflags}" '
            'LDFLAGS="{ldflags}" LIBS="-lcrypto -lsqlite3 -lqrcodegen -lrt"'
            .format(src=self._src_dir, cc=cc, cflags=cflags, ldflags=ldflags))

        binary = os.path.join(self._src_dir, "ylva")
        if not os.path.isfile(binary):
            raise ConanException("build(): make did not produce %s" % binary)
        # HMDFS/chmod guard (E046): make the artifact executable explicitly.
        os.chmod(binary, 0o755)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        licdir = os.path.join(self.package_folder, "licenses")
        for d in (bindir, mandir, licdir):
            os.makedirs(d, exist_ok=True)
        # Direct copy instead of `make install`: upstream's install target runs
        # `gzip -f` on the man page and installs into a hardcoded $(PREFIX)
        # (no DESTDIR staging), neither of which suits a relocatable package.
        # copy()'s src must be a *folder* (it walks it and fnmatches names).
        copy(self, "ylva", src=self._src_dir, dst=bindir, keep_path=False)
        copy(self, "ylva.1", src=self._src_dir, dst=mandir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=licdir,
             keep_path=False)
        exe = os.path.join(bindir, "ylva")
        if not os.path.isfile(exe):
            raise ConanException("package(): missing build artifact %s" % exe)
        os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Application package: nothing to re-export to consumers, but the CLI
        # must be resolvable through PATH in VirtualRunEnv (test_package).
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
