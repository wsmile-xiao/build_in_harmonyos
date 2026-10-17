#!/usr/bin/env python3
"""Conan recipe for libe-book-tools 0.1.3 — the command-line e-book converters.

libe-book is the Document Liberation Project's import filter for Palm-era
reflowable e-book formats (PalmDoc, Plucker, PeanutPress/eReader, zTXT,
TealDoc, RocketBook, TomeRaider) plus FictionBook 2, BBeB, EPUB/OPF and HTML.
This recipe is the *converter* half of that source tree: it configures the
official 0.1.3 dist tarball with tools enabled and packages the three programs
built from src/conv/{raw,text,html} — ebook2raw, ebook2text, ebook2html.

Why a separate package from libe-book
-------------------------------------
The platform tracks the library and its converters as two tasks (libe-book
0.1.4 and libe-book-tools 0.1.3), and archives/l/libe-book/0.1.4/conanfile.py
documents the same decision from the other side (``--without-tools``, "W2
atomicity keeps this recipe a pure library").  The split mirrors the
libmspub / libmspub-tools pair already in the archive.  Accordingly this
package ships ``bin/`` and licenses only: no ``lib/``, no ``include/``.
Packaging libe-book-0.1.a a second time under a different reference would
hand any consumer that requires both packages two archives defining the same
symbols.

Why 0.1.3 and not 0.1.4
-----------------------
0.1.3 is the version named by the task card and by the branch gate (L0n/R40
cross-checks the version directory against the branch), and upstream publishes
an official 0.1.3 dist tarball, so the coordinate is exact and self-consistent.
A dist tarball is required rather than a source-control archive: the OHOS
device has no autoconf/automake/libtoolize, so only the tarball's pre-generated
``configure`` (GNU Autoconf 2.72) can drive this build.

Upstream tests
--------------
``src/test/`` registers one cppunit program in both ``check_PROGRAMS`` and
``TESTS``, built by ``--enable-tests`` (upstream default), so ``make check``
in build() is the real upstream gate.  Which translation units take part is
configuration-dependent: EBOOKLanguageManagerTest needs liblangtag (absent
from the artifact repository — see archives/l/libe-book/0.1.4 notes), and
XMLCollectorTest / XMLTreeWalkerTest need ``--enable-experimental`` (libcss,
hubbub, mspack), so the compiled suite is EBOOKBitStreamTest +
EBOOKMemoryStreamTest + PDBLZ77StreamTest + SoftBookLZSSStreamTest.  The
assertions actually run are reported by cppunit itself in the build log.

OHOS machinery
--------------
Everything below is carried over from the CI-green libe-book 0.1.4 recipe for
the *same* source family, each item re-probed against this tarball:

* Compilers pinned from the profile: conan's AutotoolsToolchain writes CC/CXX
  into a script only conan's own Autotools() helper sources, so a raw
  subprocess must be handed them directly, or autoconf falls back to a bare
  ``clang`` that cannot link OHOS executables on a CI worker.
* Shell: /data/service/hnp/bin/bash.  toybox /system/bin/sh rejects the
  ``exec 7<&0`` style redirections this generated configure uses.
* ``umask 077`` -> ``umask 022`` in the generated configure: its scratch
  directory is untraversable on hmdfs, where traversal is decided by group
  bits that ``chmod`` cannot set (E011 family).
* Triplets ``--build=aarch64-unknown-linux-gnu`` /
  ``--host=aarch64-unknown-linux-gnu``: this dist carries 2013-vintage
  config.sub/config.guess, which reject the musl and ohos forms that libe-book
  0.1.4's newer aux scripts accept, so the triplet pair was re-measured against
  this tarball instead of inherited.
* In-tree build: the source is copied into the build folder before configuring.
* Every PKG_CHECK_MODULES pair is preset with both halves non-empty, because an
  empty half falls through to pkg-config and hard-fails (libetonyek lesson).
* librevenge is linked through a directory holding only ``.a`` files: its
  ``.la`` records ``libdir='//lib'`` (prefix=/ plus DESTDIR) and libtool aborts
  with "library was moved" otherwise (libwpd lesson).
* libxml2 is a versioned shared library, linked from its own package directory
  with ``-Wl,-rpath`` baked into the executables so they resolve
  ``libxml2.so.16`` at run time without LD_LIBRARY_PATH (which breaks lld on at
  least one CI worker).
"""

import hashlib
import os
import shlex
import shutil
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

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "bash", "/usr/bin/zsh")

# Installed by src/conv/*/Makefile.am; everything else `make install` writes is
# part of the library package, not this one.
TOOLS = ("ebook2raw", "ebook2text", "ebook2html")


class LibebookToolsConan(ConanFile):
    name = "libe-book-tools"
    version = "0.1.3"
    description = ("Command-line converters for reflowable e-book formats "
                   "(ebook2raw, ebook2text, ebook2html)")
    license = "MPL-2.0"
    homepage = "https://sourceforge.net/p/libebook/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ebook", "converter", "document-liberation")

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("librevenge/0.0.5")
        # The converters link the public libe-book library built in this tree,
        # whose own link line needs libxml2, zlib and ICU; the tools add the
        # generators and stream halves of librevenge on top (see
        # src/conv/*/Makefile.am LDADD).
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1")
        self.requires("icu4c/77")

    def build_requirements(self):
        # Header-only use by libe-book's and the tools' own translation units.
        self.tool_requires("boost/1.90.0.3")
        # Upstream's cppunit suite is enabled by --enable-tests (default on).
        self.tool_requires("cppunit/1.15.1")
        # AC_PATH_PROG([GPERF]) is fatal: src/lib's BUILT_SOURCES compile six
        # *.gperf token tables into *.inc at build time.
        self.tool_requires("gperf/3.3")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libe-book-tools is adapted for Linux and OHOS, not "
                f"{self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require arch=armv8 (aarch64)")

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official LibreOffice release tarball.

        Explicit download rather than conan's get()/download(): the CA trust
        store is resolved from certifi or $CONAN_HOME/cacert.pem with a hard
        failure when neither exists, and a failing download reports its URL and
        HTTP status instead of a FileNotFoundError naming the destination.
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
        self._keep_tools_only()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # Nothing to link against: this package delivers executables only, and
        # the library half is libe-book/<version>.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            # This dist's config.sub/config.guess are the 2013 versions: they
            # reject `aarch64-unknown-linux-musl' and `...-ohos' ("machine
            # `aarch64-unknown-linux' not recognized") and normalise
            # `aarch64-linux-gnu' to `aarch64-unknown-linux-gnu'.  The plain GNU
            # pair is what the merged libmspub-tools recipe uses for the same
            # reason.  libe-book 0.1.4 ships a newer config.sub that does accept
            # musl, so that conclusion had to be re-measured here rather than
            # copied: aux-script vintage differs between dist tarballs.
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--disable-dependency-tracking",
            # The point of this package: src/conv/{raw,text,html}. It also sets
            # need_stream/need_generators in configure.
            "--with-tools",
            # --enable-tests (the upstream default) builds src/test/'s cppunit
            # program so `make check` runs it in build().
            "--enable-tests",
            # liblangtag has an archive with status published but is absent
            # from the artifact repository (a pipeline gap, not a missing
            # task), matching the documented degraded path of libe-book 0.1.4.
            "--without-liblangtag",
            # Documentation needs doxygen and installs nothing this package
            # would keep.
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
            # check_PROGRAMS and TESTS, so `make check` runs it.  A failure
            # fails the package build.
            self._run_ohos("make -j1 check")

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again (E490)."""
        for relative in ("configure", "config.guess", "config.sub",
                         "install-sh", "missing", "depcomp", "compile",
                         "ltmain.sh", "config.status", "ar-lib",
                         "mkinstalldirs"):
            path = Path(self.build_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)

    def _relax_umask_in_configure(self):
        """Rewrite `umask 077` -> `umask 022` in the generated configure."""
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

    def _keep_tools_only(self):
        """Drop the library/install tree, keeping bin/ and licenses/."""
        keep = {"bin", "licenses"}
        removed = []
        for entry in sorted(os.listdir(self.package_folder)):
            path = Path(self.package_folder, entry)
            if entry in keep or not path.is_dir():
                continue
            shutil.rmtree(path)
            removed.append(entry)
        if removed:
            self.output.info(
                f"[ok] libe-book-tools keeps bin/ only, dropped {removed}")
        bindir = Path(self.package_folder, "bin")
        missing = [tool for tool in TOOLS
                   if not (bindir / tool).is_file()]
        if missing:
            raise ConanException(
                f"expected converter binaries not packaged: {missing}")
        for tool in TOOLS:
            (bindir / tool).chmod(0o755)

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
        # Neutralize LD_LIBRARY_PATH rather than extending it: the musl loader
        # consults it before the SDK's own rpath, and both known ambient values
        # are poison — the CI worker's /usr/local/lib (incompatible
        # libxml2.so.16 breaks lld, CI-021 build #48068) and the device's
        # <sdk>/native/llvm/lib, which the profile puts on LD_LIBRARY_PATH and
        # which ships its own libxml2.so.16 (2.14.0) alongside our dependency's
        # 2.15.3.1.  Nothing needs it: a plain C++ program compiled by this SDK
        # runs with an empty LD_LIBRARY_PATH on the device (measured), and the
        # just-built test programs find libxml2 through the -Wl,-rpath baked
        # into their link line (see _dependency_environment_items).
        environment.define("LD_LIBRARY_PATH", "")
        compiler_items = self._compiler_environment_items()
        for name, value in compiler_items.items():
            environment.define(name, value)
        # E012 / E528: the profile gives absolute compiler paths but keeps the
        # native toolchain directory out of this subprocess' PATH, so autotools
        # archiver discovery misses (`<triplet>-ar`, `ar`, `lib`, `link` all
        # absent — OHOS ships llvm-ar, never binutils' ar) and libtool degrades
        # to `AR=false`.  Exporting the four tool variables AND putting their
        # directory on PATH is the documented closure; configure probes some of
        # the rest by name.
        tool_dir = os.path.dirname(compiler_items.get("CC", ""))
        if tool_dir:
            environment.prepend_path("PATH", tool_dir)
        for name, value in self._dependency_environment_items().items():
            environment.define(name, value)
        # AC_PATH_PROG([GPERF]) is fatal and src/lib compiles *.gperf tables
        # through BUILT_SOURCES, so gperf must be reachable by name.
        environment.prepend_path(
            "PATH", str(Path(self.dependencies.build["gperf"].cpp_info.bindirs[0])
                         .resolve()))
        return environment

    def _compiler_environment_items(self):
        """CC/CXX from the profile's tools.build:compiler_executables, plus the
        binutils that autoconf/libtool probe by name (E012: the OHOS SDK ships
        llvm-ar, never binutils' `ar`; E528 records the resulting
        "could not determine false interface" and this closure).

        The toolchain script holding these is sourced only by conan's own
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
        items = {variable: compilers[key]
                 for key, variable in mapping.items() if compilers.get(key)}
        directory = os.path.dirname(items.get("CC") or items.get("CXX") or "")
        if directory:
            for variable, tool in (("AR", "llvm-ar"), ("RANLIB", "llvm-ranlib"),
                                   ("NM", "llvm-nm"), ("STRIP", "llvm-strip"),
                                   ("LD", "ld.lld")):
                candidate = os.path.join(directory, tool)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    items[variable] = candidate
        return items

    def _dependency_environment_items(self):
        """<PREFIX>_CFLAGS/_LIBS for every PKG_CHECK_MODULES call.

        With --with-tools and --enable-tests, configure.ac runs five module
        checks beyond boost: librevenge, librevenge-stream,
        librevenge-generators, libxml-2.0, zlib, icu-i18n and cppunit.  The
        generators pair is the one this recipe adds over libe-book 0.1.4 —
        without it configure falls back to pkg-config, the published .pc files
        carry libdir='//lib', and with_tools silently degrades to no.
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
        ambient_cxx = os.environ.get("CXXFLAGS", "")
        # The project is C++11 (AX_CXX_COMPILE_STDCXX_11), which adds no -std
        # flag when the compiler default already satisfies it; the profile
        # declares cppstd=17, so pin the standard rather than exceed it.
        cxxflags = " ".join(filter(None, ["-std=c++17", ambient_cxx]))
        link = f"-L{self._clean_link_dir()}"
        xml_link = f"-L{xml2}/lib"
        zlib_link = f"-L{zlib}/lib"
        icu_link = f"-L{icu}/lib"
        rpath = f"-Wl,-rpath,{xml2}/lib"
        return {
            "BOOST_CFLAGS": boost_include,
            "CPPFLAGS": cppflags,
            "CXXFLAGS": cxxflags,
            # ICU is a C++ library shipped as static archives: the link line
            # carries all three plus libc++ for their C++ runtime symbols.
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
            "REVENGE_GENERATORS_CFLAGS": revenge_include,
            "REVENGE_GENERATORS_LIBS":
                f"{link} -lrevenge-generators-0.0 -lrevenge-0.0 "
                f"{xml_link} -lxml2 {zlib_link} -lz {rpath} -lm",
            "XML_CFLAGS": xml_include,
            "XML_LIBS": f"{xml_link} -lxml2 {zlib_link} -lz {rpath} -lm",
            "ZLIB_CFLAGS": f"-I{zlib}/include",
            "ZLIB_LIBS": f"{zlib_link} -lz",
        }

    def _clean_link_dir(self):
        """Directory holding the librevenge archives, and no `.la` file."""
        clean = Path(self.build_folder, ".dependency-libs")
        clean.mkdir(parents=True, exist_ok=True)
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
            "zsh cannot run automake's recursive make)")

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
        """Evidence for a failed step, printed into the captured build log."""
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
                        f"downloaded {len(payload)} bytes (HTTP {status})")
                    break
                except Exception as error:  # noqa: BLE001 - retried below
                    last = error
                    self.output.warning(
                        f"download attempt {attempt}/{attempts} failed: {error}")
            else:
                raise ConanException(
                    f"could not download {url} after {attempts} attempts: "
                    f"{last}")
        actual = hashlib.sha256(staging.read_bytes()).hexdigest()
        if actual != sha256:
            staging.unlink(missing_ok=True)
            raise ConanException(
                f"sha256 mismatch for {url}: expected {sha256}, got {actual}")
        staging.replace(destination)
