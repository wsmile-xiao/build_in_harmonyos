#!/usr/bin/env python3
"""Conan recipe for libe-book 0.1.4 — reflowable e-book import library.

libe-book is the Document Liberation Project's import filter for Palm-era
e-book formats (PalmDoc, Plucker, PeanutPress/eReader, zTXT, TealDoc,
RocketBook, TomeRaider, ...) plus FictionBook 2, BBeB, HTML and friends.  It
parses into the librevenge document model, like its siblings libetonyek /
libabw / libwpd already packaged in this archive.

configure.ac (dist tarball, GNU Autoconf 2.72 — `configure` is carried, no
autoreconf needed since the OHOS device has no automake/autoconf/libtoolize)
requires, in order:

* ``gperf`` (AC_PATH_PROG, fatal when absent) — six ``*.gperf`` token tables
  are compiled into ``*.inc`` by ``src/lib``'s BUILT_SOURCES, so this is a
  real build-time tool, satisfied through ``tool_requires("gperf/3.3")``.
* ``librevenge-0.0``, ``libxml-2.0`` and ``zlib`` (PKG_CHECK_MODULES, fatal).
* boost headers (AC_CHECK_HEADERS, fatal) — algorithm/string, optional,
  spirit, variant, ...; header-only use, so a tool_requires.
* ``icu-i18n`` (PKG_CHECK_MODULES, fatal) — from the published icu4c package
  (static icui18n/icuuc/icudata archives; cif-api precedent).  ICU is C++:
  its static archives pull libc++ symbols, so ``ICU_LIBS`` carries -lc++.
* ``liblangtag`` — optional upstream switch, disabled here (see below).
* cppunit only under ``--enable-tests``.
* ``librevenge-stream``/``librevenge-generators`` only for tools and fuzzers.

Two dependency decisions are recorded here because they shape the build:

* **liblangtag is disabled** (``--without-liblangtag``, an upstream switch),
  following the libetonyek 0.1.13 precedent: an archive exists
  (``archives/l/liblangtag/0.6.4/``, status published) but the artifact
  repository has no liblangtag — a publishing-pipeline gap, not a missing
  task.  The main library therefore takes the documented degraded path:
  language tagging of parsed text runs is unavailable, everything else is.
  The boundary is repeated in notes.md, manifest.yaml and the PR body.
* **The conversion tools are not built** (``--without-tools``).  The platform
  tracks the library and its converters as separate tasks (libe-book 0.1.4
  and libe-book-tools 0.1.3), mirroring the libmspub / libmspub-tools split
  already in the archive; W2 atomicity keeps this recipe a pure library (no
  commands.json, no generators requirement).

Upstream ships its own unit suite: ``src/test/`` builds one cppunit program
(``test``) registered in both check_PROGRAMS and TESTS — enabled by
``--enable-tests`` (default yes) — so ``make check`` runs it as a hard gate
in build().  With liblangtag disabled the suite compiles the BitStream /
MemoryStream / PDBLZ77Stream / SoftBookLZSSStream TUs (the LanguageManager TU
is excluded upstream under the same switch).

OHOS machinery carried over from this archive's libetonyek / libwpd ports,
each item re-probed against this tarball first:

* **Compilers pinned from the profile.**  conan's AutotoolsToolchain writes
  CC/CXX into conanautotoolstoolchain.sh, but that script is sourced only by
  conan's own Autotools() helper; a raw subprocess never sees it.  Left
  unset, autoconf falls back to a bare ``clang`` from PATH — the hnp
  toolchain on the device, but something that cannot link OHOS executables
  on a CI worker ("C compiler cannot create executables", libcdaudio CI
  #46506).
* **Shell**: ``/data/service/hnp/bin/bash``.  toybox /system/bin/sh rejects
  constructs in this generated configure (autoconf 2.72 uses ``exec 7<&0``
  style redirections), and zsh must never be the recipe shell for automake
  trees.
* **umask 077 -> 022** in the generated configure: its scratch directory is
  created with ``umask 077`` and hmdfs decides traversal on the group bits,
  where ``chmod`` has no effect — the directory becomes untraversable and
  everything inside it fails with EACCES (E011 family).
* **Triplets**: this dist's config.sub/config.guess are the 2024 versions
  and know both ``aarch64`` and ``musl``, so the ordinary pair keeps
  build != host, i.e. cross mode, and nothing here branches on build_cpu.
* **In-tree build**: the source tree is copied into the build folder before
  configuring, as in the other recipes in this archive.
"""

import os
import shlex
import ssl
import subprocess
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


class LibebookConan(ConanFile):
    name = "libe-book"
    version = "0.1.4"
    description = ("Library for parsing reflowable e-book formats into the "
                   "librevenge document model")
    license = "MPL-2.0"
    homepage = "https://sourceforge.net/p/libebook/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("librevenge/0.0.5")
        # configure.ac checks librevenge-0.0, libxml-2.0 and zlib in three
        # separate PKG_CHECK_MODULES calls, and icu-i18n in a fourth.  zlib
        # also arrives transitively (librevenge's stream layer and libxml2
        # both use it) but is declared so the static link line is complete.
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1")
        self.requires("icu4c/77")

    def build_requirements(self):
        # Header-only dependencies used by libe-book's own translation units
        # only — they appear in neither the public headers (inc/) nor the
        # link interface, so they must not appear in cpp_info.requires.
        self.tool_requires("boost/1.90.0.3")   # boost/algorithm, optional, spirit, variant
        # Upstream's cppunit suite is enabled by --enable-tests (default on).
        self.tool_requires("cppunit/1.15.1")
        # AC_PATH_PROG([GPERF]) is fatal, and src/lib's BUILT_SOURCES compile
        # six *.gperf token tables into *.inc at build time.
        self.tool_requires("gperf/3.3")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libe-book is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official LibreOffice release tarball.

        Explicit download rather than conan's get()/download(): the CA trust
        store is resolved from conan's own certifi or $CONAN_HOME/cacert.pem
        with a hard failure when neither exists, and a failing download
        reports its URL and HTTP status instead of a FileNotFoundError
        naming the destination.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "libe-book-source.tar.xz")
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
            autotools.make(target="check")

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._package_ohos()
        else:
            Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libe-book")
        self.cpp_info.set_property("cmake_target_name", "libe-book::libe-book")
        self.cpp_info.set_property("pkg_config_name", "libe-book-0.1")
        self.cpp_info.libs = ["e-book-0.1"]
        self.cpp_info.includedirs = ["include/libe-book-0.1"]
        # Each entry is "<conan package>::<component>", and for a dependency
        # that defines no components the whole package is addressed by
        # repeating its name.  Conan is strict about both halves: a bare
        # "libxml2" is read as an *internal component*, and the CMake target
        # name "LibXml2::LibXml2" is rejected because the package would have
        # to be called LibXml2 ("not a direct requirement of the recipe").
        # The public headers expose only librevenge types, so icu4c is on
        # this list for the static link line (its archives are linked into
        # the static libe-book archive), not for headers.
        self.cpp_info.requires = ["librevenge::librevenge",
                                  "libxml2::libxml2", "zlib::zlib",
                                  "icu4c::icu4c"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            # build != host keeps configure in cross mode (configure never
            # runs the programs it compiles).  This dist's config.sub is the
            # 2024 version and knows both `aarch64` and `musl`, so the
            # ordinary pair works.
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--disable-dependency-tracking",
            # --enable-tests (the upstream default) builds src/test/'s
            # cppunit program so `make check` runs it in build().
            "--enable-tests",
            # AGENTS.md §3.7: liblangtag has an archive with status published
            # but is absent from the artifact repository (a pipeline gap, not
            # a missing task), so the main library takes the documented
            # degraded path — see the module docstring and notes.md.
            "--without-liblangtag",
            # The library and the conversion tools are tracked as separate
            # platform tasks (libe-book / libe-book-tools), mirroring the
            # libmspub / libmspub-tools split in this archive; W2 atomicity
            # keeps this package a pure library.
            "--without-tools",
            # Documentation needs doxygen and is not part of the library.
            "--without-docs",
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
            # R34/R51: upstream's own suite — src/test/ registers `test` in
            # check_PROGRAMS and TESTS, so `make check` runs it (cppunit;
            # enabled by --enable-tests).  A failure fails the build.
            self._run_ohos("make -j1 check")

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

        Device-verified (ncrack, libcaca, libcdaudio, libetonyek): the
        scratch dir is created with `umask 077` giving mode 2700, and hmdfs
        decides traversal on the group bits where `chmod` is a no-op, so the
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
        # Explicitly neutralize LD_LIBRARY_PATH: the musl loader consults
        # it before the SDK's own rpath, and at least one CI worker carries
        # an ambient LD pointing at /usr/local/lib whose incompatible
        # libxml2.so.16 breaks lld (which links libxml2 for itself):
        #   Error relocating .../llvm/bin/lld: xmlFreeDoc: symbol not found
        # (CI-021 build #48068).  The just-built test programs still find
        # the shared libraries through -Wl,-rpath baked into their link
        # line (see _dependency_environment_items), which lld honours at
        # link time without touching the loader path.
        environment.define("LD_LIBRARY_PATH", "")
        for name, value in self._compiler_environment_items().items():
            environment.define(name, value)
        for name, value in self._dependency_environment_items().items():
            environment.define(name, value)
        # AC_PATH_PROG([GPERF]) is fatal and src/lib compiles *.gperf tables
        # through BUILT_SOURCES, so the gperf binary from the tool_requires
        # must be reachable by name.
        environment.prepend_path(
            "PATH", str(Path(self.dependencies.build["gperf"].cpp_info.bindirs[0])
                         .resolve()))
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

    def _dependency_environment_items(self):
        """<PREFIX>_CFLAGS/_LIBS for every PKG_CHECK_MODULES call.

        configure.ac checks five modules on this configuration — librevenge,
        libxml-2.0, zlib, icu-i18n and (because --enable-tests is on)
        cppunit plus librevenge-stream — and the build environment has
        pkg-config, so each check must be satisfied by handing it the
        variable pair it would otherwise ask pkg-config for; PKG_CHECK_MODULES
        uses those verbatim when the CFLAGS half is non-empty, and BOTH
        HALVES MUST BE NON-EMPTY: the macro short-circuits each half
        independently, and an empty half falls through to pkg-config, which
        then fails the check with an as_fn_error (libetonyek, mdds,
        device-verified).

        Every `*_LIBS` also carries the transitive archives the static
        dependencies need (zlib for librevenge's stream layer and libxml2,
        libm for libxml2, libc++ for icu4c's C++ static archives — cif-api
        precedent).  All dependency libraries are referenced through a
        directory that holds only the archives, never libtool `.la` files
        (see _clean_link_dir), except libxml2, which is a versioned shared
        library linked from its own package directory with an rpath.
        """
        revenge = self.dependencies["librevenge"].package_folder
        xml2 = self.dependencies["libxml2"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        icu = self.dependencies["icu4c"].package_folder
        boost_include = (
            f"-I{self.dependencies.build['boost'].package_folder}/include")
        cppunit = self.dependencies.build["cppunit"]
        revenge_include = f"-I{revenge}/include/librevenge-0.0"
        xml_include = f"-I{xml2}/include/libxml2 -I{xml2}/include"
        ambient = os.environ.get("CPPFLAGS", "")
        cppflags = " ".join(filter(None, [boost_include, ambient]))
        # The project is a C++11 one (AX_CXX_COMPILE_STDCXX_11), which adds
        # *no* -std flag when the compiler's default already satisfies
        # C++11 — the SDK's clang 15 defaults to gnu++14.  The profile
        # declares cppstd=17, so pinning the standard here matches the
        # platform profile rather than exceeding it (libetonyek precedent
        # for its C++17 dependency headers).
        ambient_cxx = os.environ.get("CXXFLAGS", "")
        cxxflags = " ".join(filter(None, ["-std=c++17", ambient_cxx]))
        # librevenge ships libtool `.la` files, so it goes through the clean
        # directory; libxml2 is a versioned shared library linked from its
        # own directory (and must not be copied around); zlib and icu4c are
        # packaged without `.la` files.
        link = f"-L{self._clean_link_dir()}"
        xml_link = f"-L{xml2}/lib"
        zlib_link = f"-L{zlib}/lib"
        icu_link = f"-L{icu}/lib"
        # Bake the shared libraries' directories into every test program's
        # RUNPATH so `make check` resolves libxml2.so.16 at run time without
        # this recipe ever having to set LD_LIBRARY_PATH (which breaks lld).
        # musl honours DT_RUNPATH.
        rpath = f"-Wl,-rpath,{xml2}/lib"
        return {
            "BOOST_CFLAGS": boost_include,
            "CPPFLAGS": cppflags,
            "CXXFLAGS": cxxflags,
            # ICU is a C++ library shipped as static archives: the link line
            # carries all three archives plus libc++ for their C++ runtime
            # symbols and the package's own system_libs (cif-api precedent).
            "ICU_CFLAGS": f"-I{icu}/include",
            "ICU_LIBS": f"{icu_link} -licui18n -licuuc -licudata -lc++ -lm",
            "CPPUNIT_CFLAGS": f"-I{cppunit.package_folder}/include",
            "CPPUNIT_LIBS": f"-L{cppunit.package_folder}/lib -lcppunit",
            "REVENGE_CFLAGS": revenge_include,
            "REVENGE_LIBS":
                f"{link} -lrevenge-0.0 {xml_link} -lxml2 {zlib_link} -lz "
                f"{rpath} -lm",
            "REVENGE_STREAM_CFLAGS": revenge_include,
            "REVENGE_STREAM_LIBS":
                f"{link} -lrevenge-stream-0.0 -lrevenge-0.0 "
                f"{xml_link} -lxml2 {zlib_link} -lz {rpath} -lm",
            "XML_CFLAGS": xml_include,
            "XML_LIBS": f"{xml_link} -lxml2 {zlib_link} -lz {rpath} -lm",
            "ZLIB_CFLAGS": f"-I{zlib}/include",
            "ZLIB_LIBS": f"{zlib_link} -lz",
        }

    def _clean_link_dir(self):
        """Directory holding the librevenge archives, and no `.la` file.

        libtool resolves `-l<name>` by looking for a matching `.la` in the
        `-L` directories first, and the `.la` shipped by a dependency records
        the libdir it was installed for (`//lib`, because the recipes use
        prefix=/ plus DESTDIR).  That makes a cross-package link fail with

            libtool: warning: library '.../librevenge-0.0.la' was moved.
            libtool: error: cannot find the library '//lib/librevenge-0.0.la'

        (device-verified on libwpd).  Naming the archives by absolute path
        instead makes libtool treat them as input *members* and archive them
        into the produced static library, which clashes with the same library
        linked by a consumer.  Linking against a directory that contains only
        the archives keeps libtool on the plain `-L/-l` path.
        """
        clean = Path(self.build_folder, ".dependency-libs")
        clean.mkdir(parents=True, exist_ok=True)
        # Only the librevenge package ships `.la` files; the loop is kept
        # over a tuple so a future dependency that starts shipping them can
        # be added here.
        for reference in ("librevenge",):
            folder = Path(self.dependencies[reference].package_folder, "lib")
            if not folder.is_dir():
                continue
            for suffix in (".a", ".so"):
                for source in sorted(folder.glob(f"*{suffix}")):
                    destination = clean / source.name
                    if not destination.exists():
                        copy(self, source.name, src=str(source.parent),
                             dst=str(clean), keep_path=False)
        return clean

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
        completed = subprocess.run(
            command + " < /dev/null", shell=True, env=environment,
            cwd=cwd or self.build_folder, stdin=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            self._dump_failure_diagnostics(cwd or self.build_folder,
                                           environment)
            raise ConanException(
                f"OHOS build step failed (rc={completed.returncode}): {command}"
            )

    def _dump_failure_diagnostics(self, directory, environment):
        """Evidence for a failed step, printed into the captured build log.

        A CI worker's log is the only observation point this recipe gets on
        that fleet, and a bare

            configure: error: C compiler cannot create executables

        says nothing about which value TMPDIR/LD_LIBRARY_PATH/PATH actually
        had when the compiler test ran, nor what config.log recorded of the
        clang invocation.  Print both so the next diagnosis runs on facts.
        """
        self.output.info("---- ohos diagnostics: environment ----")
        for name in ("CC", "CXX", "CPPFLAGS", "LDFLAGS", "LIBS", "CFLAGS",
                     "CXXFLAGS", "TMPDIR", "LD_LIBRARY_PATH", "PKG_CONFIG_PATH"):
            if name in environment:
                self.output.info(f"{name}={environment[name]}")
        self.output.info(f"PATH={environment.get('PATH', '')}")
        config_log = Path(directory, "config.log")
        if not config_log.is_file():
            self.output.info("no config.log in the failing directory")
            return
        text = config_log.read_text(errors="replace")
        marker = "checking whether the C compiler works"
        start = text.rfind(marker)
        window = text[start:] if start != -1 else text[-4000:]
        self.output.info("---- config.log: last compiler-test block ----")
        for line in window.splitlines()[:14]:
            self.output.info(line)

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
                except Exception as error:  # noqa: BLE001 - retried below
                    last = error
                    self.output.warning(
                        f"download attempt {attempt}/{attempts} failed: {error}")
            else:
                raise ConanException(
                    f"could not download {url} after {attempts} attempts: {last}")
        import hashlib
        actual = hashlib.sha256(staging.read_bytes()).hexdigest()
        if actual != sha256:
            staging.unlink(missing_ok=True)
            raise ConanException(
                f"sha256 mismatch for {url}: expected {sha256}, got {actual}")
        staging.replace(destination)
