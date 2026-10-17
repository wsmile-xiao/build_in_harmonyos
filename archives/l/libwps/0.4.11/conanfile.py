#!/usr/bin/env python3
"""Conan recipe for libwps 0.4.11 — Microsoft Works document parser library.

libwps reads Microsoft Works documents (text, spreadsheet and database
 flavours), plus a family of legacy DOS formats (Microsoft Write, Word for
DOS, Multiplan, Quattro Pro, Lotus 1-2-3, XYWrite).  It is a Document
Liberation Project library and builds on librevenge, the shared document
model.  Build system is autotools with a dist-carried `configure`
(GNU Autoconf 2.69), so no autoreconf is needed — the OHOS device has no
automake/autoconf/libtoolize.

Dependency wiring (configure.ac of this dist): libwps finds librevenge with
`PKG_CHECK_MODULES([REVENGE],[librevenge-0.0])` and — because
`--enable-tools` defaults to *yes* — two more checks for
`librevenge-generators-0.0` and `librevenge-stream-0.0` (the conversion
tools need them).  Unlike its sibling libwpd, libwps has **no boost
requirement**: no AC_CHECK_HEADERS for boost, and no boost include in its
sources, so the recipe stays with librevenge + zlib only.  zlib itself is
not probed by configure but is needed at link time because librevenge is a
static library whose stream layer links zlib (`-lz`).

The device has no pkg-config, so the three `<PREFIX>_CFLAGS`/`<PREFIX>_LIBS`
variable pairs are exported from the package folder instead;
PKG_CHECK_MODULES prefers those over pkg-config by design.

OHOS machinery (carried over from this author's libwpd 0.10.3 port, each
item re-probed against this tarball first):

* **Compilers pinned from the profile.**  conan's AutotoolsToolchain writes
  `CC`/`CXX` into conanautotoolstoolchain.sh, but that script is sourced only
  by conan's own Autotools() helper; a raw subprocess never sees it.  Left
  unset, autoconf falls back to a bare `clang` from PATH — the hnp toolchain
  on the device, but something that cannot link OHOS executables on a CI
  worker ("C compiler cannot create executables", libcdaudio CI #46506).
* **Shell**: `/data/service/hnp/bin/bash`.  This configure (autoconf 2.69)
  contains `exec 7<&0`, which toybox `/system/bin/sh` rejects; bash also
  gives the POSIX IFS word splitting automake's recursive make needs (zsh
  does not, and zsh must never be the recipe shell for automake trees).
* **umask 077 -> 022** in the generated configure: its scratch directory is
  created with `umask 077` (mode 2700) and hmdfs decides traversal on the
  group bits, where `chmod` has no effect — the directory becomes
  untraversable and everything inside it fails with EACCES.
* **Triplets**: this dist's `config.sub` is dated 2013-10-01.  It knows
  `aarch64` but still not `musl`, so `aarch64-…-musl` is rejected while a
  four-part name carrying the `unknown` vendor passes through; the pair below
  keeps build != host, i.e. cross mode, and nothing here branches on
  build_cpu.
* **In-tree build**: the source tree is copied into the build folder before
  configuring, as in the other recipes in this archive.
* **Docs off**: configure probes for doxygen and would warn; the package
  ships no API doc that a consumer needs, so `--without-docs` keeps the
  build lean.  Fuzzers stay off (upstream default).

Upstream ships no test suite (no `TESTS`/`check_PROGRAMS`, no test sources,
no `src/test/`), so test_package/ carries the verification: it drives the
format detector and the parse entry points through the public libwps API
with a hand-built Microsoft Works v2 header, and exercises the packaged
conversion tools end to end.
"""

import hashlib
import os
import shlex
import ssl
import time
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, unzip)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class LibwpsConan(ConanFile):
    name = "libwps"
    version = "0.4.11"
    description = ("Library for reading and converting Microsoft Works "
                   "documents (and several legacy DOS formats)")
    license = "LGPL-2.1-or-later OR MPL-2.0"
    homepage = "https://sourceforge.net/projects/libwps/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("librevenge/0.0.5")
        # librevenge is static and links zlib for its stream layer; the
        # REVENGE*_LIBS pairs below carry -lz so consumers do not have to.
        self.requires("zlib/1.3.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libwps is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official SourceForge release tarball.

        Explicit download rather than conan's get()/download(): the CA trust
        store is resolved from conan's own certifi or $CONAN_HOME/cacert.pem
        with a hard failure when neither exists (AGENTS.md §1.2), and a
        failing download reports its URL and HTTP status instead of a
        FileNotFoundError naming the destination.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "libwps-source.tar.bz2")
        self._fetch(source["url"], archive, source["sha256"])
        unzip(self, str(archive), destination=self.source_folder,
              strip_root=True)
        archive.unlink()

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._configure_args())
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._build_ohos()
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._package_ohos()
        else:
            Autotools(self).install()
        copy(self, "COPYING.LGPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "COPYING.MPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libwps")
        self.cpp_info.set_property("cmake_target_name", "libwps::libwps")
        self.cpp_info.set_property("pkg_config_name", "libwps-0.4")
        self.cpp_info.libs = ["wps-0.4"]
        self.cpp_info.includedirs = ["include/libwps-0.4"]
        self.cpp_info.requires = ["librevenge::librevenge", "zlib::zlib"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            # build != host keeps configure in cross mode.  2013-10-01
            # config.sub: `aarch64` is known, `musl` is not, so the pair used
            # for newer dists is rejected — a four-part name with the
            # `unknown` vendor passes through untouched.
            "--build=arm-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--disable-dependency-tracking",
            "--without-docs",
            # --enable-tools is upstream's default (yes); the six conversion
            # tools (wps2html/wps2raw/wps2text/wks2csv/wks2raw/wks2text) are
            # kept so no capability is dropped.  Fuzzers stay off (default).
        ]

    # ── OHOS build machinery ────────────────────────────────────────────

    def _build_ohos(self):
        shell = self._resolve_shell()
        copy(self, "*", src=self.source_folder, dst=self.build_folder)
        self._restore_script_modes()
        self._relax_umask_in_configure()
        with self._build_environment().vars(self).apply():
            self._run_ohos(
                f"{shlex.quote(shell)} ./configure "
                f"{' '.join(shlex.quote(a) for a in self._configure_args())}"
            )
            self._run_ohos("make -j1")

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again (E490)."""
        candidates = [
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ltmain.sh", "config.status",
            "ar-lib", "mkinstalldirs",
        ]
        for relative in candidates:
            path = Path(self.build_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)

    def _relax_umask_in_configure(self):
        """Rewrite `umask 077` -> `umask 022` in the generated configure.

        Device-verified (ncrack, libcaca, libcdaudio, libwpd): the scratch
        dir is created with `umask 077` giving mode 2700, and hmdfs decides
        traversal on the group bits where `chmod` is a no-op, so the
        directory is untraversable (EACCES on everything inside it).  022
        yields `drwxr-s--x`.
        """
        path = Path(self.build_folder, "configure")
        if not path.is_file():
            raise ConanException(f"configure script is missing: {path}")
        content = path.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException(
                f"umask contract changed in configure: expected 2 "
                f"occurrences of {needle!r}, found {content.count(needle)}"
            )
        path.write_text(content.replace(needle, "umask 022"),
                        encoding="utf-8", newline="\n")

    def _package_ohos(self):
        shell = self._resolve_shell()
        with self._build_environment().vars(self).apply():
            destination = shlex.quote(self.package_folder)
            self._run_ohos(f"make -j1 install DESTDIR={destination}")

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        for name, value in self._compiler_environment_items().items():
            environment.define(name, value)
        for name, value in self._revenge_environment_items().items():
            environment.define(name, value)
        return environment

    def _compiler_environment_items(self):
        """CC/CXX from the profile's tools.build:compiler_executables.

        The toolchain script holding them is sourced only by conan's own
        Autotools() helper, so a raw subprocess must be given them directly
        (R33: the toolchain comes from a declared source, not from PATH).
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if not compilers:
            return {}
        if isinstance(compilers, str):
            import json
            try:
                compilers = json.loads(compilers)
            except ValueError:
                return {}
        mapping = {"c": "CC", "cpp": "CXX"}
        return {variable: compilers[key]
                for key, variable in mapping.items() if compilers.get(key)}

    def _revenge_environment_items(self):
        """REVENGE*_CFLAGS/_LIBS for libwps's three PKG_CHECK_MODULES calls.

        No pkg-config on the device, so configure must be handed the
        variables it would otherwise ask pkg-config for; PKG_CHECK_MODULES
        uses them verbatim when they are non-empty.  librevenge is static,
        hence the trailing -lz from its own stream layer in every pair.

        The librevenge libraries are referenced through a **clean -L
        directory** that holds only the archives, not the `.la` files (see
        _clean_link_dir below for why naming them directly fails).
        """
        revenge = self.dependencies["librevenge"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        include = f"-I{revenge}/include/librevenge-0.0"
        link_zlib = f"-L{zlib}/lib -lz"
        link_dir = self._clean_link_dir()
        link = f"-L{link_dir}"
        return {
            "REVENGE_CFLAGS": include,
            "REVENGE_LIBS": f"{link} -lrevenge-0.0 {link_zlib}",
            "REVENGE_GENERATORS_CFLAGS": include,
            "REVENGE_GENERATORS_LIBS":
                f"{link} -lrevenge-generators-0.0 -lrevenge-0.0 {link_zlib}",
            "REVENGE_STREAM_CFLAGS": include,
            "REVENGE_STREAM_LIBS":
                f"{link} -lrevenge-stream-0.0 -lrevenge-0.0 {link_zlib}",
        }

    def _clean_link_dir(self):
        """Directory holding just the librevenge archives, no `.la` files.

        libtool resolves `-lrevenge-0.0` by looking for a matching `.la` in
        the `-L` directories first, and the `.la` shipped in the package
        records the libdir it was installed for (`//lib`, from prefix=/ plus
        DESTDIR), so the link dies with

            libtool: warning: library '.../librevenge-0.0.la' was moved.
            libtool: error: cannot find the library '//lib/librevenge-0.0.la'

        Naming the archive by absolute path avoids that but makes libtool
        treat the archive as an input *member*, embedding it into
        libwps-0.4.a ("archive member 'librevenge-0.0.a' is neither ET_REL
        nor LLVM bitcode") — which then clashes with the librevenge archive a
        consumer links.  Linking against a directory that contains only the
        archives keeps libtool on the plain `-L/-l` path with no `.la` to
        misread.
        """
        clean = Path(self.build_folder, ".revenge-libs")
        clean.mkdir(parents=True, exist_ok=True)
        for name in ("revenge-0.0", "revenge-generators-0.0",
                     "revenge-stream-0.0"):
            source = Path(self._revenge_archive(name))
            destination = clean / source.name
            if not destination.exists():
                copy(self, source.name, src=str(source.parent),
                     dst=str(clean), keep_path=False)
        return clean

    def _revenge_archive(self, name):
        """Absolute path of one librevenge library file.

        Static archives are preferred, matching how the librevenge recipe is
        packaged (static by default); the shared object is used when that is
        what the package actually carries.
        """
        folder = Path(self.dependencies["librevenge"].package_folder, "lib")
        for suffix in (".a", ".so"):
            candidate = folder / f"lib{name}{suffix}"
            if candidate.is_file():
                return str(candidate)
        raise ConanException(
            f"librevenge library lib{name}.a/.so not found under {folder}"
        )

    def _resolve_shell(self):
        for candidate in OHOS_SHELL_CANDIDATES:
            if os.path.sep in candidate:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
                continue
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                path = os.path.join(directory, candidate)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
        raise ConanInvalidConfiguration(
            "no suitable shell found on OHOS (need the hnp bash or zsh; "
            "zsh cannot run automake's recursive make)"
        )

    def _run_ohos(self, command, cwd=None):
        shell = self._resolve_shell()
        environment = dict(os.environ)
        environment["SHELL"] = shell
        environment["CONFIG_SHELL"] = shell
        import subprocess
        completed = subprocess.run(
            command + " < /dev/null", shell=True, env=environment,
            cwd=cwd or self.build_folder, stdin=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            raise ConanException(
                f"OHOS build step failed (rc={completed.returncode}): {command}"
            )

    # ── download helpers ────────────────────────────────────────────────

    def _ca_bundle(self):
        candidates = []
        try:
            import certifi
            candidates.append(certifi.where())
        except ImportError:
            pass
        conan_home = os.getenv("CONAN_HOME") or os.path.join(
            os.path.expanduser("~"), ".conan2")
        candidates.append(os.path.join(conan_home, "cacert.pem"))
        candidates.append(os.getenv("SSL_CERT_FILE") or "")
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "no CA bundle found for the source download: looked for certifi's "
            "cacert, $CONAN_HOME/cacert.pem and $SSL_CERT_FILE"
        )

    def _fetch(self, url, destination, sha256, attempts=3):
        destination = Path(destination)
        staging = destination.with_name(destination.name + ".part")
        if url.startswith("file:"):
            from urllib.parse import urlparse
            from urllib.request import url2pathname
            import shutil
            shutil.copyfile(url2pathname(urlparse(url).path), staging)
        else:
            context = ssl.create_default_context(cafile=self._ca_bundle())
            last = None
            for attempt in range(1, attempts + 1):
                try:
                    request = urllib.request.Request(
                        url, headers={"User-Agent": "conan"})
                    with urllib.request.urlopen(request, timeout=120,
                                                context=context) as response:
                        payload = response.read()
                        status = response.status
                    staging.write_bytes(payload)
                    self.output.info(
                        f"downloaded {len(payload)} bytes (HTTP {status}) "
                        f"from {url}")
                    break
                except Exception as error:  # noqa: BLE001 - reported verbatim
                    last = error
                    self.output.warning(
                        f"download attempt {attempt}/{attempts} failed for "
                        f"{url}: {type(error).__name__}: {error}")
                    if staging.exists():
                        staging.unlink()
                    if attempt < attempts:
                        time.sleep(5)
            else:
                raise ConanException(f"could not download {url}: {last}")

        digest = hashlib.sha256(staging.read_bytes()).hexdigest()
        if digest != sha256:
            staging.unlink()
            raise ConanException(
                f"sha256 mismatch for {url}: expected {sha256}, got {digest}")
        os.replace(staging, destination)
