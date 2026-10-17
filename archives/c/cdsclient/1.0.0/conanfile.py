#!/usr/bin/env python3
"""Conan recipe — cdsclient 1.0.0 (CDS astronomical data client).

cdsclient is the CDS (Centre de Données astronomiques de Strasbourg)
'vizier.c.cdsclient' package — a command-line interface to query the
VizieR catalogue database, Simbad, and other CDS services.

Build system: autotools (configure + make). The released tarball ships a
pre-generated Autoconf 2.69 configure script, so no autoreconf is needed.
No external dependencies (sockets + libc only).

Build products:
  bin/aclient         — the C client (non-interactive mode works offline:
                        `aclient -version` / `-h` exit 0 without any server)
  bin/find*, vizquery, catcat, lscat, catClient.py, ... — ~90 shell/client
                        scripts that query CDS services (need network/CDS)
  share/man           — man pages (sk.3, aclient.1, wwwget.1)
  versions            — version marker file

OHOS adaptations (see notes.md):
  - configure: HMFS/HMDFS doesn't support getcwd → `pwd` fallback to $PWD
    (same as aribb24/1.0.4, xsel/1.2.1); E114 umask 077 → 022 so that
    config.status can create its temp dir. Patch 0001.
  - aclient.c: HarmonyOS libc.so does not export getpass() → getpasswd()
    rewritten with POSIX termios (tcgetattr/tcsetattr/termios.h).
    Patch 0002.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdsclientConan(ConanFile):
    name = "cdsclient"
    version = "1.0.0"
    description = "CDS client tools to query VizieR and astronomical databases"
    license = "GPL-3.0-or-later"
    homepage = "https://cdsarc.cds.unistra.fr/viz-bin/cdsclient"
    url = "https://cdsarc.cds.unistra.fr/ftp/pub/sw/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # configure checks for source files (aclient.c, sk.h, ...) in the
        # current directory to decide CASE=export vs CASE=dev.  Out-of-source
        # builds with a separate build directory won't find them, so build
        # in-source (source_folder = build_folder).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _staging_dir(self):
        # The upstream Makefile install targets use `cp -p` directly to
        # $(PREFIX)/... and ignore DESTDIR, so this staging prefix is where
        # `make install` writes.  Always use a path under the user home
        # (writable even when CI TMPDIR is owned by another user).  The
        # per-user tmp directory is separate from the clang temp dir.
        home_tmp = os.path.join(os.path.expanduser("~"), "tmp")
        return os.path.join(home_tmp, f"cdsclient-{self.version}-staging")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: no system same-name library involved (no libcdsclient.so in
        # /lib /lib64), default dynamic linking is fine — this is an
        # application package, only the `aclient` binary is link-output.
        # Set prefix to a writable per-user staging dir (the Makefile uses
        # cp -p directly to $(PREFIX)/bin, so DESTDIR doesn't apply).
        tc.configure_args.append(f"--prefix={self._staging_dir()}")
        tc.generate()

    def _writable_tmpdir(self):
        """CI worker may set TMPDIR to a path owned by another user
        (e.g. /data/storage/el2/base/cache owned by 20020102), which
        prevents clang from creating temporary files for the conftest
        test in configure → "C compiler cannot create executables".
        Return a writable per-user path for TMPDIR/TEMP/TMP."""
        home_tmp = os.path.join(os.path.expanduser("~"), "tmp")
        candidate = os.environ.get("TMPDIR") or ""
        # Only trust the inherited TMPDIR if it actually points to a
        # directory we can write to.
        if candidate and os.path.isdir(candidate):
            try:
                probe = os.path.join(candidate, ".cdsclient-write-probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                return candidate
            except OSError:
                pass
        os.makedirs(home_tmp, exist_ok=True)
        return home_tmp

    def build(self):
        # HMFS/HMDFS doesn't support getcwd: chdir to build_folder so that
        # relative path lookup works, and pre-set PWD so the shell `pwd`
        # builtin falls back to the logical path (same as xsel/1.2.1,
        # aribb24/1.0.4). configure patch 0001 adds the same $PWD fallback
        # for `ac_pwd`.
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder

        # Force a writable TMPDIR/TEMP/TMP so clang/configure conftest
        # compiles in sub-processes that inherited a non-writable TMPDIR
        # from the CI worker. Restore the original values afterwards.
        tmpdir = self._writable_tmpdir()
        os.makedirs(tmpdir, exist_ok=True)
        saved = {}
        try:
            for _k in ("TMPDIR", "TEMP", "TMP"):
                saved[_k] = os.environ.get(_k)
                os.environ[_k] = tmpdir
            apply_conandata_patches(self)
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            # The Makefile install targets use `cp -p` directly to
            # $(PREFIX)/... and do NOT honor DESTDIR.  --prefix is set to a
            # writable per-user staging dir in generate(); the Makefile uses
            # plain `mkdir` (no -p), so create the parent before installing.
            # Use `-j1` to avoid the HMFS jobserver fifo issue (mkfifo
            # Operation not permitted on HMFS).
            staging = self._staging_dir()
            os.makedirs(staging, exist_ok=True)
            self.run("make install", env="conanbuild")  # 串行 install：make4.4 jobserver 在 HMFS 上 mkfifo 被拒
        finally:
            for _k, _v in saved.items():
                if _v is None:
                    os.environ.pop(_k, None)
                else:
                    os.environ[_k] = _v

    def package(self):
        # The upstream Makefile installs with `cp -p` to $(PREFIX)/bin and
        # $(PREFIX)/man (no $(INSTALL), no DESTDIR support). generate() sets
        # --prefix to a writable per-user staging dir, build() runs `make
        # install` to populate it, and this package() copies the staged
        # files into package_folder.
        staging = self._staging_dir()
        for subdir in ("bin", "man"):
            src = os.path.join(staging, subdir)
            if os.path.isdir(src):
                copy(self, "*", src, os.path.join(self.package_folder, subdir))
        versions_src = os.path.join(staging, "versions")
        if os.path.isfile(versions_src):
            copy(
                self,
                "versions",
                staging,
                os.path.join(self.package_folder, "share", self.name),
            )
        # aclient binary must be executable
        aclient = os.path.join(self.package_folder, "bin", "aclient")
        if os.path.isfile(aclient):
            os.chmod(aclient, 0o755)

    def package_info(self):
        # Command-line tool package: aclient + client shell scripts in bin/.
        # No linkable library (no include/ lib/ artifacts).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]