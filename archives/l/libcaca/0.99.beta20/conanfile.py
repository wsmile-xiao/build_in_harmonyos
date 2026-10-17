#!/usr/bin/env python3
"""Conan recipe for libcaca 0.99.beta20 — colour ASCII art library.

libcaca renders text as coloured ASCII art: canvas composition, blitting,
dithering, figlet fonts and bitmap-to-ASCII transforms, plus a set of
output drivers (ncurses, slang, X11, GL, raw, ...).  The installed artifact
is the C library `libcaca` (with `libcaca++` when the C++ bindings are
enabled) — the project itself is a C codebase: exactly one configure
script at the top level (autotools), 92 `.c` sources for the library and
tools against 8 `.cpp` sources for the optional C++ binding.

Language note (R47): `configs/lang-preflight` reports `python` for this
tarball because it prioritises *manifests* over the build system and the
dist ships the optional SWIG binding under `python/setup.py`.  That file
belongs to the `python/` binding sub-package, not to the project: the top
level is `configure.ac` + `Makefile.am` + a pre-generated `configure`, and
the artifact is a C ABI library.  The Python / Ruby / Java / C# bindings
are all explicitly disabled below, so the delivered package contains only
the C (and optionally C++) library.  Per AGENTS.md §1.2 the language is
judged on the project's主体 — autotools + C — which is in scope.

Dependencies: zlib is a hard requirement — `caca/file.c` implements the
stream layer with gzopen()/gzgets(), autodetected via
`AC_CHECK_HEADERS(zlib.h)` + `AC_CHECK_LIB(z, gzopen)` and with no
configure switch to turn it off.  ncurses provides the terminal driver
(option `with_ncurses`); the X11/GL/Cocoa/Win32/conio/VGA/kernel backends
and the language bindings are disabled — none of them has a published
dependency or a target system in common with this port.

OHOS machinery (device-verified for this author's previous autotools
recipes, ncrack 0.7 / 2026-09-13; each item was re-probed against *this*
tarball before being encoded):

* **Shell**: this `configure` is autoconf 2.71 and also saves stdin with
  `exec 7<&0`, which `/system/bin/sh` (toybox) rejects ("7<&0 : bad file
  descriptor").  Fix: run configure under `/usr/bin/zsh` with
  `CONFIG_SHELL` exported (configure self-re-execs before reaching that
  line), stdin redirected from /dev/null because the worker job starts with
  fd 0 closed.
* **Triplets**: the shipped `.auto/config.sub` is dated 2018-02-22 and
  knows neither `ohos` nor `harmonyos`, so `--build`/`--host` are both
  given explicitly with config.sub-clean values that still differ
  (cross mode — configure then never tries to *execute* conftest
  binaries, which the build host cannot do).
* **umask 077 -> 022 in the generated configure**: the script creates its
  scratch directory with `(umask 077 && mktemp -d "./confXXXXXX")`, which
  yields mode 2700.  hmdfs mediates access through the group bits (every
  hmdfs directory is `drwxrws--x`) and `chmod` is a no-op there, so a
  group-untraversable 2700 directory makes every later read inside it fail
  with EACCES.  Rewriting the umask to 022 yields `drwxr-s--x`.
* **In-tree build**: the build copies the source tree into the build
  folder before configuring, matching the other recipes in this archive
  and keeping the layout independent of VPATH behaviour.

Tests: upstream's own `make check` suite is executed during `build()` —
`TESTS = simple check-copyright check-source check-win32 caca-test`, where
`caca-test` (12 cppunit cases across canvas/dirty/driver/export) is
enabled through the `cppunit` test requirement.  Upstream's CI only runs
`./configure && make`, so this is strictly stronger than upstream's gate.
"""

import glob
import os
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, unzip)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Shell used for every build step.  bash (hnp toolchain) first — it is what
# the platform profile declares as the build shell, it word-splits unquoted
# expansions like POSIX sh, and it supports the multi-digit fd redirection
# autoconf's `exec 7<&0` needs.  zsh is kept as a fallback for the configure
# step only in spirit: it runs autoconf fine but must not be the recipe shell
# for automake trees, because zsh does *not* split unquoted `$var` on IFS —
# automake's `for subdir in $list; do cd $subdir; done` then receives the whole
# SUBDIRS string as a single directory name
# ("zsh:cd: no such file or directory: kernel caca src examples tools ...",
# device-verified).  /system/bin/sh (toybox) is deliberately absent: it cannot
# run autoconf's fd-7 redirection.
OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class LibcacaConan(ConanFile):
    name = "libcaca"
    version = "0.99.beta20"
    description = ("Colour ASCII art library: canvas composition, blitting, "
                   "dithering and multiple output drivers")
    license = "WTFPL"
    homepage = "https://github.com/cacalabs/libcaca"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "with_ncurses": [True, False],
    }
    default_options = {
        "shared": False,
        "with_ncurses": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The ncurses backend is the only driver that is both meaningful on
        # a PC terminal and backed by a published package; it is what makes
        # cacaview/img2txt usable, so it stays on by default.
        if self.options.with_ncurses:
            self.requires("ncurses/6.4")
        # caca/file.c uses gzopen()/gzgets()/gzread() (caca_file_* stream
        # layer), autodetected with AC_CHECK_HEADERS(zlib.h) +
        # AC_CHECK_LIB(z, gzopen) and with no way to switch it off.  It must
        # therefore be a declared requirement — without it the static
        # libcaca.a carries references to -lz that no consumer can resolve
        # (device-verified: test_package link failed on gzgets/gzopen).
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # Upstream's own unit suite (caca/t) is cppunit-based and is run by
        # `make check` during build(); --enable-cppunit is passed so a
        # missing cppunit is a hard error instead of a silent skip.
        #
        # tool_requires, not test_requires: cppunit is consumed by this
        # recipe's own build (caca-test is a noinst_PROGRAM), and Conan 2
        # keeps test_requires out of `self.dependencies` until the
        # test_package runs — reading it from generate() raises
        # "KeyError: 'cppunit' not found in the dependency set"
        # (device-verified, verify run 1).
        self.tool_requires("cppunit/1.15.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcaca is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch the official release tarball, then unpack it in place.

        The download is done here rather than with conan's ``get()`` /
        ``download()`` helpers, for two reasons established on this platform:

        * **CA trust store (AGENTS.md §1.2).**  The CI worker has none of the
          device-side bundle paths, so the trust store is resolved from
          conan's own ``certifi.where()`` and ``$CONAN_HOME/cacert.pem``, and
          a missing bundle is a hard error instead of a silent fallback to an
          unverified context.
        * **Failure shape.**  ``download()`` reports a transient TLS failure
          against the injected mirror as ``FileNotFoundError`` naming the
          destination file — a message that says nothing about the network
          and hides which URL was tried (device-verified, verify run 1).
          Fetching explicitly keeps the URL, the HTTP status and the checksum
          in the log.

        The official release asset is required rather than the
        ``archive/refs/tags`` zip: only the release asset carries the
        autotools dist files, i.e. the pre-generated `configure` — the OHOS
        device has no automake/autoconf/libtoolize, so autoreconf is not an
        option.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "libcaca-source.tar.gz")
        self._fetch(source["url"], archive, source["sha256"])
        unzip(self, str(archive), destination=self.source_folder,
              strip_root=True)
        os.remove(str(archive))

    # ── download helpers ────────────────────────────────────────────────

    def _ca_bundle(self):
        """Resolve a CA bundle, or fail fast (AGENTS.md §1.2)."""
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
        import hashlib
        import ssl
        import time
        import urllib.request

        destination = Path(destination)
        staging = destination.with_name(destination.name + ".part")
        if url.startswith("file:"):
            from urllib.request import url2pathname
            from urllib.parse import urlparse
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
                    # Written through a staging file so a failed attempt can
                    # never leave a truncated archive behind for unzip().
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

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._configure_args())
        toolchain.generate()
        # Dependency include/library paths for ncurses.  AutotoolsToolchain
        # alone does not export CPPFLAGS/LDFLAGS (device-verified), so the
        # configure checks for ncursesw/ncurses.h and -lncursesw would not
        # find the packaged headers without this generator.
        AutotoolsDeps(self).generate()
        # cppunit is detected through pkg-config; point it at the packaged
        # .pc directory so the check cannot depend on host state.  The
        # CPPUNIT_CFLAGS/CPPUNIT_LIBS pair is what actually decides the
        # check (configure prefers the environment over pkg-config), and it
        # is exported from _build_environment() because generate()'s saved
        # script is not sourced by the plain subprocess that runs configure.
        cppunit = self.dependencies.build["cppunit"]
        environment = Environment()
        environment.define(
            "PKG_CONFIG_PATH",
            os.path.join(cppunit.package_folder, "lib", "pkgconfig"))
        environment.vars(self).save_script("conanbuildenv_libcaca_cppunit")

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._build_ohos()
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            autotools.make(args=["-j1", "check"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._package_ohos()
        else:
            Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libcaca")
        self.cpp_info.set_property("cmake_target_name", "libcaca::libcaca")
        self.cpp_info.components["caca"].libs = ["caca"]
        self.cpp_info.components["caca"].set_property(
            "cmake_target_name", "libcaca::caca")
        self.cpp_info.components["caca"].requires = ["zlib::zlib"]
        if self.options.with_ncurses:
            self.cpp_info.components["caca"].requires.append(
                "ncurses::ncurses")
        # libcaca++ is built only when the C++ bindings are enabled, which
        # follows the presence of a C++ compiler (autodetected); the clang
        # toolchain always provides one, so the component is declared.
        self.cpp_info.components["caca++"].libs = ["caca++"]
        self.cpp_info.components["caca++"].set_property(
            "cmake_target_name", "libcaca::caca++")
        self.cpp_info.components["caca++"].requires = ["caca"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        arguments = [
            # build != host -> configure stays in cross mode and never runs
            # the programs it compiles; both triplets explicit so the 2018
            # config.guess/config.sub pair is never asked about `ohos`.
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-gnu",
            # prefix=/ + DESTDIR=<package_folder> (see _package_ohos) places
            # include/ and lib/ at the package root instead of nesting them
            # under usr/local/.
            "--prefix=/",
            # R26: system-name libraries default to static.
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            # Backends: ncurses is the only one with a published package and
            # a terminal on the target; the rest target systems this port
            # does not run on (X11/GL/Cocoa/Win32/DOS conio/VGA kernel mode)
            # or have no published dependency (slang, imlib2).
            "--enable-ncurses" if self.options.with_ncurses else "--disable-ncurses",
            "--disable-slang",
            "--disable-x11",
            "--disable-gl",
            "--disable-cocoa",
            "--disable-conio",
            "--disable-win32",
            "--disable-vga",
            "--disable-kernel",
            "--disable-network",
            "--disable-imlib2",
            # Language bindings are out of scope for this archive: only the
            # C library (and its C++ binding) is built and packaged.
            "--disable-java",
            "--disable-python",
            "--disable-ruby",
            "--disable-csharp",
            # Documentation needs doxygen/LaTeX and zzuf fuzzing is not
            # available; neither affects the shipped library.
            "--disable-doc",
            "--disable-zzuf",
            # Upstream unit suite (caca/t) — enabled on purpose, see
            # build_requirements().
            "--enable-cppunit",
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
            # R34/R51: upstream's own suite (simple, check-copyright,
            # check-source, check-win32 and the 12-case cppunit caca-test).
            # A failure fails the build.
            self._run_ohos("make -j1 check")

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again.

        E490: helper scripts (`configure`, `.auto/config.guess`,
        `.auto/config.sub`, `install-sh`, `missing`, `depcomp`, `ltmain.sh`,
        `compile`, `config.status` and the `build/autotools/*` helpers) are
        programs, and a copy that loses the executable bit makes `make`
        fail with "Permission denied" as soon as one is invoked directly
        rather than through $(SHELL).
        """
        candidates = [
            "configure",
            os.path.join(".auto", "config.guess"),
            os.path.join(".auto", "config.sub"),
            "install-sh",
            "missing",
            "depcomp",
            "compile",
            "ltmain.sh",
            "config.status",
            "caca-config",
        ]
        candidates += glob.glob(
            os.path.join(self.build_folder, "build", "autotools", "*"))
        for relative in candidates:
            path = Path(self.build_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)

    def _relax_umask_in_configure(self):
        """Rewrite `umask 077` -> `umask 022` in the generated configure.

        Device-verified root cause (2026-09-13, ncrack 0.7 and reproduced
        here by inspection of this tarball): configure and config.status
        create their scratch directory with
        `(umask 077 && mktemp -d "./confXXXXXX")`, giving mode 2700.  hmdfs
        mediates directory access through the group bits and `chmod` has no
        effect there, so the directory is untraversable and every later
        read inside it fails with EACCES.  The umask is the only lever:
        022 produces `drwxr-s--x`.  This tarball has a single configure
        script (`AC_CONFIG_AUX_DIR(.auto)`, no AC_CONFIG_SUBDIRS), so one
        file is enough.
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
        # Dependency paths have to be exported here: the generated
        # conanautotoolsdeps.sh holds them, but it is sourced by conan's own
        # Autotools() helper — this recipe runs configure through a plain
        # subprocess, and conan does not apply the build env to os.environ
        # (device-verified: config.log recorded CPPFLAGS with only the
        # ambient -I<prefix>/include, and all four ncurses header probes
        # failed while conanautotoolsdeps.sh carried the right -I path).
        # The ambient values are kept, after ours.
        cppflags, ldflags, libs = [], [], []
        if self.options.with_ncurses:
            ncurses = self.dependencies["ncurses"].package_folder
            cppflags.append(f"-I{ncurses}/include")
            ldflags.append(f"-L{ncurses}/lib")
            libs.extend(["-lformw", "-lmenuw", "-lpanelw", "-lncursesw"])
        # Prepended, so the packaged zlib wins over any header the device
        # happens to have under its own prefix: the ambient CPPFLAGS below
        # point at $HOME/usr/local/include, where a foreign zlib.h made
        # configure enable zlib support against a library no consumer links
        # (device-verified).
        zlib = self.dependencies["zlib"].package_folder
        cppflags.insert(0, f"-I{zlib}/include")
        ldflags.insert(0, f"-L{zlib}/lib")
        libs.insert(0, "-lz")
        for name, value in (("CPPFLAGS", cppflags), ("LDFLAGS", ldflags),
                            ("LIBS", libs)):
            ambient = os.environ.get(name, "")
            parts = [*value, ambient] if ambient else list(value)
            if parts:
                environment.define(name, " ".join(parts))
        # configure prefers these over pkg-config for the cppunit check, and
        # the device has no pkg-config at all (probe-verified), so the check
        # only passes because both are set here.
        cppunit = self.dependencies.build["cppunit"].package_folder
        environment.define("CPPUNIT_CFLAGS", f"-I{cppunit}/include")
        environment.define("CPPUNIT_LIBS", f"-L{cppunit}/lib -lcppunit")
        return environment

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
            "no autoconf-capable shell found on OHOS (need /usr/bin/zsh or "
            "bash; /system/bin/sh cannot run autoconf's `exec 7<&0`)"
        )

    def _run_ohos(self, command, cwd=None):
        """Run one build step with the OHOS shell contract applied."""
        shell = self._resolve_shell()
        environment = dict(os.environ)
        environment["SHELL"] = shell
        environment["CONFIG_SHELL"] = shell
        # fd 0 is closed in the worker job environment; autoconf's
        # `exec 7<&0` needs a live descriptor to duplicate.
        result = self._exec(command + " < /dev/null", environment, cwd)
        if result != 0:
            raise ConanException(
                f"OHOS build step failed (rc={result}): {command}"
            )

    def _exec(self, command, environment, cwd):
        import subprocess
        completed = subprocess.run(
            command, shell=True, env=environment, cwd=cwd or self.build_folder,
            stdin=subprocess.DEVNULL,
        )
        return completed.returncode
