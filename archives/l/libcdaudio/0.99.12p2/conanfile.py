#!/usr/bin/env python3
"""Conan recipe for libcdaudio 0.99.12p2 — portable audio CD library.

libcdaudio drives audio CD playback (`cd_init_device`, `cd_play_track`,
`cd_poll`, ...) and bundles CDDB/CDIndex lookup, cover-art fetch and the
base64 helper.  Everything lives in one flat `src/` directory; the dist
tarball carries a pre-generated `configure` (GNU Autoconf 2.59, 2005), so no
autoreconf is needed — the OHOS device has no automake/autoconf/libtoolize.

The library has genuinely hardware-free logic worth testing: the
LBA/MSF/frame conversion helpers and the version reporting, plus the
documented graceful failure of `cd_init_device()` when the device node does
not exist.  Upstream ships **no test suite** (no `TESTS`/`check_PROGRAMS`
in any Makefile.am, no test sources), so verification is carried by
test_package/.

OHOS machinery (carried over from this author's libcaca 0.99.beta20 port,
re-probed against this tarball before use):

* **Shell**: the platform profile declares `/data/service/hnp/bin/bash` as
  the build shell and that is what is used.  Unlike libcaca, this configure
  (autoconf 2.59) contains no `exec 7<&0`, so toybox `/system/bin/sh` would
  probably do; bash is still required for automake's recursive make, whose
  `for subdir in $list` depends on POSIX IFS word splitting that zsh does
  not perform.
* **umask 077 -> 022 in the generated configure**: it creates its scratch
  directory with `(umask 077 && mktemp -d -q "./confstatXXXXXX")`, i.e. mode
  2700.  hmdfs mediates directory access through the group bits (every hmdfs
  directory is `drwxrws--x`) and `chmod` is a no-op there, so the directory
  is untraversable and everything inside it fails with EACCES.
* **Triplets**: the shipped `config.sub` is dated 2005-04-25 and knows
  neither `ohos` nor `harmonyos`; `--build`/`--host` are both given
  explicitly with config.sub-clean values that differ, which keeps configure
  in cross mode so it never tries to execute the programs it compiles.
* **In-tree build**: the source tree is copied into the build folder before
  configuring, matching the other recipes in this archive.

The installed header and library keep upstream's naming: because the host is
neither BeOS nor Irix, `cdaudioname` stays `cdaudio`, so the package installs
`include/cdaudio.h` and links as `-lcdaudio`.
"""

import glob
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
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, unzip)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# bash first: it is the shell the platform profile declares, it word-splits
# unquoted expansions like POSIX sh (automake's recursive make needs that),
# and it handles autoconf's multi-digit fd redirection if a configure uses
# it.  zsh is kept as a fallback but must not be the recipe shell for
# automake trees.  /system/bin/sh (toybox) is deliberately absent.
OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class LibcdaudioConan(ConanFile):
    name = "libcdaudio"
    version = "0.99.12p2"
    description = ("Portable library for audio CD playback control, with "
                   "CDDB/CDIndex lookup and cover-art support")
    license = "GPL-2.0-or-later"
    homepage = "https://libcdaudio.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcdaudio is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official SourceForge release tarball.

        Downloaded explicitly rather than with conan's get()/download()
        helpers: the CA trust store is resolved from conan's own certifi or
        $CONAN_HOME/cacert.pem with a hard failure when neither exists
        (AGENTS.md §1.2), and a failing download reports its URL and HTTP
        status instead of a FileNotFoundError that names the destination.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "libcdaudio-source.tar.gz")
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
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cdaudio")
        self.cpp_info.set_property("cmake_target_name", "cdaudio::cdaudio")
        self.cpp_info.set_property("pkg_config_name", "libcdaudio")
        self.cpp_info.libs = ["cdaudio"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        arguments = [
            # build != host keeps configure in cross mode, so it never tries
            # to *run* the programs it compiles.
            #
            # The triplets are chosen for what this dist's config.sub accepts:
            # it is dated 2005-04-25 and knows neither `aarch64` (added to
            # config.sub around 2012) nor `musl`, so the aarch64-…-musl /
            # aarch64-…-gnu pair used for libcaca is rejected outright
            # ("machine `aarch64-unknown-linux' not recognized").  A four-part
            # name with the `unknown` vendor passes through untouched, so
            # `aarch64-unknown-linux-gnu` is accepted as the host; the build
            # triplet only has to be accepted and differ, and nothing in this
            # codebase branches on build_cpu.  `arm-unknown-linux-gnu` is a
            # triplet the 2005 script canonicalises cleanly.
            "--build=arm-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            # prefix=/ + DESTDIR=<package_folder> puts include/ and lib/ at
            # the package root instead of nesting them under usr/local/.
            "--prefix=/",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--disable-dependency-tracking",
            # --enable-threads is upstream's default ("guessed") and probes
            # for pthread_create; when the probe fails it simply leaves
            # threading off, so the default is kept rather than forced.
        ]
        return arguments

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
            # Upstream registers no tests (no TESTS/check_PROGRAMS in any
            # Makefile.am), so there is nothing to run here; test_package/
            # carries the verification instead.

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again (E490)."""
        candidates = [
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ltmain.sh", "config.status",
            "mkinstalldirs",
        ]
        for relative in candidates:
            path = Path(self.build_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)

    def _relax_umask_in_configure(self):
        """Rewrite `umask 077` -> `umask 022` in the generated configure.

        Device-verified root cause (2026-09-13, ncrack and libcaca): the
        scratch directory is created with `umask 077`, giving mode 2700.
        hmdfs decides directory traversal on the group bits and `chmod` has
        no effect there, so the directory cannot be entered and every later
        read inside it fails with EACCES.  The umask is the only lever:
        022 yields `drwxr-s--x`.  This tarball has a single configure script.
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
        return environment

    def _compiler_environment_items(self):
        """CC/CXX taken from the profile's tools.build:compiler_executables.

        conan's AutotoolsToolchain writes exactly these into
        conanautotoolstoolchain.sh, but that script is sourced by conan's own
        Autotools() helper — a raw subprocess never sees it (libcaca lesson),
        so the compile step would run with CC unset.  autoconf then falls back
        to a bare `clang` from PATH, which happens to be the hnp toolchain on
        the device but not on a CI worker: there the clang found this way
        cannot link OHOS executables, and configure dies with
        "C compiler cannot create executables" (CI build #46506).
        Pinning the compiler explicitly is also what R33 asks for — the
        toolchain comes from a declared source, not from PATH.
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
        # fd 0 is closed in the worker job environment; autoconf's
        # `exec 7<&0` (when present) needs a live descriptor to duplicate.
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
