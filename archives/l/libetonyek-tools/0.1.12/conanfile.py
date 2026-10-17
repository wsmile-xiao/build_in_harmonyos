#!/usr/bin/env python3
"""Conan recipe — libetonyek-tools 0.1.12 (the eonyek command-line converters).

libetonyek parses Apple iWork documents (Keynote / Pages / Numbers) and exports
them through the librevenge document model.  Its source tree carries, besides
the library, a set of nine command-line converters under `src/conv/`:

    src/conv/raw    key2raw  numbers2raw  pages2raw
    src/conv/text   key2text numbers2text pages2text
    src/conv/csv    numbers2csv
    src/conv/html   pages2html
    src/conv/svg    key2xhtml

Upstream builds them whenever `--with-tools` is not disabled (AC_ARG_WITH([tools])
has no default, and the AS_IF test `x$with_tools != xno` therefore evaluates
true), so the *libraries* archive that carries only libetonyek-0.1.a is a
different deliverable from these binaries.  This recipe packages the tools —
the same split Debian makes with its `libetonyek-tools` binary package — and
installs nothing but bin/ plus the license.

The tools link `src/lib/libetonyek-0.1.la` from the same tree, so the library is
built here rather than taken from libetonyek/<version>: that keeps this package
self-contained and lets `make check` exercise the very code that was linked in.

Deps mirror archives/l/libetonyek/0.1.13 (same configure.ac, verified against
this tarball):

* requires librevenge/0.0.5, libxml2/2.15.3.1, zlib/1.3.1 — the three the link
  line actually needs at run time.
* tool_requires boost/1.90.0.3, glm/1.0.3, mdds/3.2.1 (private headers used by
  libetonyek's own translation units; none appear in the installed interface of
  a bin-only package) and cppunit/1.15.1 (the upstream suite).
* configure.ac's `$(BOOST_FILESYSTEM_LIB)` / `$(BOOST_SYSTEM_LIB)` in
  src/conv/*/Makefile.am are *not* AC_SUBST'ed by this configure.ac — the boost
  macros it calls only probe headers — so those references expand to nothing and
  no boost library is needed.  Verified: `grep -c BOOST_FILESYSTEM_LIB configure`
  is 0 while src/conv/*/Makefile.in does carry the @...@ placeholder.

liblangtag is disabled (`--without-liblangtag`, an upstream switch): the
sibling libetonyek/0.1.13 recipe records that archives/l/liblangtag/0.6.4/ is
archived with `status: published` yet absent from the artifact registry, which
is a publishing-pipeline gap rather than a missing task.  Language tagging of
text spans is the only thing lost; the conversion output itself is unaffected.

Upstream ships a real test suite and this recipe runs it: `--enable-tests`
(default yes) builds `src/test/`, whose Makefile.am sets
`tests = core detection streams`, `check_PROGRAMS = $(tests)` and
`TESTS = $(tests)`, so `make -j1 check` runs all three cppunit programs.  A
failing check fails the build — see notes.md for the case counts.

OHOS machinery, carried over from archives/l/libetonyek/0.1.13 and re-probed
against this tarball:

* **Compilers pinned from the profile.**  AutotoolsToolchain writes CC/CXX into
  conanautotoolstoolchain.sh, which only conan's own Autotools() helper sources;
  a raw subprocess never sees it, and autoconf then falls back to a bare `clang`
  from PATH — the hnp toolchain on the device, but something that cannot link
  OHOS executables on a CI worker ("C compiler cannot create executables").
* **Shell**: /data/service/hnp/bin/bash.  This configure contains `exec 7<&0`,
  which toybox /system/bin/sh rejects; bash also gives the POSIX IFS word
  splitting automake's recursive make needs.
* **umask 077 -> 022** in the generated configure: its scratch directory is
  created under umask 077 (mode 2700) and hmdfs decides traversal on the group
  bits, where chmod has no effect — everything inside then fails with EACCES.
* **Triplet pair** --build=aarch64-unknown-linux-musl
  --host=aarch64-unknown-linux-gnu: build != host keeps configure in cross mode
  so it never runs a compiled program, which is what makes `make check` (a host
  execution on a cross build) an explicit, device-side step rather than a
  configure-time one.
* **In-tree build**: the source tree is copied into the build folder before
  configuring, because `src/test/` needs $(top_srcdir)/src/test/data.
"""

import hashlib
import os
import shlex
import shutil
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


def _ohos_shell_candidates():
    """Shells that can drive this configure, best first.

    /data/service/hnp/bin/bash exists on the CI workers only; the device
    carries harmonybrew's bash instead.  A bare toybox /system/bin/sh cannot
    (this configure uses `exec 7<&0`), and zsh must be last — its word
    splitting breaks automake's recursive make.
    """
    home = os.path.expanduser("~")
    return ("/data/service/hnp/bin/bash",
            os.path.join(home, ".harmonybrew/bin/bash"),
            "/usr/bin/bash", "bash", "/usr/bin/zsh")


# Cross-mode tool prefixes autoconf would otherwise look for as
# `aarch64-unknown-linux-musl-ar` (absent on both the device and the workers).
# The OHOS profile declares these in its [env] section, but that section is
# only applied through conan's own runners; this recipe drives configure as a
# raw subprocess, so they are re-declared here from PATH.  Without AR the
# probe degrades to `AR=false` and automake dies with
#   configure: error: could not determine false interface
_BINUTILS = (("AR", ("llvm-ar", "ar")),
             ("RANLIB", ("llvm-ranlib", "ranlib")),
             ("NM", ("llvm-nm", "nm")),
             ("STRIP", ("llvm-strip", "strip")),
             # libtool's _LT_PATH_LD probes `<host>-ld` then `ld` and aborts
             # with "no acceptable ld found in $PATH" when neither exists —
             # which is the device's case: the SDK ships ld.lld only.
             ("LD", ("ld", "ld.lld", "llvm-ld")))

# bin_PROGRAMS of src/conv/{raw,text,csv,html,svg} — the whole deliverable.
EONYEK_TOOLS = ("key2raw", "numbers2raw", "pages2raw",
                "key2text", "numbers2text", "pages2text",
                "numbers2csv", "pages2html", "key2xhtml")


class LibetonyekToolsConan(ConanFile):
    name = "libetonyek-tools"
    version = "0.1.12"
    description = ("Command-line converters for Apple iWork documents "
                   "(key2raw/key2text/numbers2csv/pages2html/…) built from "
                   "the libetonyek 0.1.12 release")
    license = "LGPL-2.1-or-later OR MPL-2.0"
    homepage = "https://wiki.documentfoundation.org/Development/libetonyek"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("librevenge/0.0.5")
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # Header-only dependencies of libetonyek's own translation units.
        self.tool_requires("boost/1.90.0.3")   # boost/algorithm, boost/optional, boost/spirit
        self.tool_requires("glm/1.0.3")        # AC_CHECK_HEADERS(glm/glm.hpp) is fatal
        self.tool_requires("mdds/3.2.1")       # published package is API 3.0
        # Upstream's cppunit suite is built with --enable-tests.
        self.tool_requires("cppunit/1.15.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libetonyek-tools is adapted for Linux and OHOS, not "
                f"{self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official LibreOffice release tarball.

        Explicit download rather than conan's get(): the CA trust store is
        resolved from certifi or $CONAN_HOME/cacert.pem with a hard failure when
        neither exists, and a failing download should report its URL and HTTP
        status rather than a FileNotFoundError naming the destination.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "libetonyek-tools-source.tar.xz")
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
            autotools.make("check")

    def package(self):
        # Install the whole tree into a staging root, then take only the nine
        # converters and the license: everything else in this build (the static
        # library, the private headers, the check programs) belongs to the
        # libetonyek package, not to this one.
        staging = Path(self.build_folder, "install-root")
        if str(self.settings.os) == "OHOS":
            self._install_ohos(staging)
        else:
            autotools = Autotools(self)
            autotools.install(args=[f"DESTDIR={staging}"])
        binding = Path(staging, "bin")
        for tool in EONYEK_TOOLS:
            built = Path(binding, tool)
            if not built.is_file():
                raise ConanException(
                    f"converter was not installed: {built} — src/conv/ is built "
                    "only when --with-tools is not disabled")
            copy(self, tool, src=str(binding),
                 dst=os.path.join(self.package_folder, "bin"),
                 keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # Bin-only package: no headers, no archives to link against.  The
        # requires list keeps the shared libxml2/zlib on the run path of
        # whoever invokes the converters.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.requires = ["librevenge::librevenge",
                                  "libxml2::libxml2", "zlib::zlib"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            # Static everywhere: the converters embed libetonyek, and this is a
            # bin-only package so there is no ABI surface to publish.
            "--enable-static", "--disable-shared",
            "--disable-dependency-tracking",
            # The deliverable.  Default-on upstream, spelled out here because
            # package() raises if it did not take effect.
            "--with-tools",
            # --enable-tests builds src/test/ (core/detection/streams) so the
            # upstream suite can run via `make check` in build().
            "--enable-tests",
            "--without-liblangtag",   # see the module docstring
            "--with-mdds=3.0",       # published mdds carries API 3.0 headers
            "--without-docs",        # needs doxygen; not part of this package
            "--disable-fuzzers",
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
            # Upstream's own suite: src/test/ registers core, detection and
            # streams in TESTS.  A failure fails the package.
            self._run_ohos("make -j1 check")

    def _install_ohos(self, staging):
        shell = self._resolve_shell()
        with self._build_environment().vars(self).apply():
            self._run_ohos("make -j1 install "
                           f"DESTDIR={shlex.quote(str(staging))}")

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again (E490)."""
        for relative in ("configure", "config.guess", "config.sub",
                         "install-sh", "missing", "depcomp", "compile",
                         "ltmain.sh", "config.status", "ar-lib",
                         "mkinstalldirs", "test-driver"):
            path = Path(self.build_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)

    def _relax_umask_in_configure(self):
        path = Path(self.build_folder, "configure")
        if not path.is_file():
            raise ConanException(f"configure script is missing: {path}")
        content = path.read_text(encoding="utf-8")
        needle = "umask 077"
        found = content.count(needle)
        if found != 2:
            raise ConanException(
                f"umask contract changed in configure: expected 2 occurrences "
                f"of {needle!r}, found {found}")
        path.write_text(content.replace(needle, "umask 022"),
                        encoding="utf-8", newline="\n")

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        # Neutralize LD_LIBRARY_PATH on purpose: the musl loader consults it
        # before the SDK's own rpath, and at least one CI worker carries an
        # ambient LD pointing at /usr/local/lib whose incompatible libxml2.so.16
        # breaks lld, which links libxml2 for itself.  The just-built programs
        # find their shared libraries through the baked-in RUNPATH instead
        # (see _dependency_environment_items).
        environment.define("LD_LIBRARY_PATH", "")
        for name, value in self._binutils_environment_items().items():
            environment.define(name, value)
        for name, value in self._compiler_environment_items().items():
            environment.define(name, value)
        for name, value in self._dependency_environment_items().items():
            environment.define(name, value)
        return environment

    def _binutils_environment_items(self):
        """AR/RANLIB/NM/STRIP/LD for the cross-mode tool probes.

        With build != host, autoconf looks these up as
        `aarch64-unknown-linux-musl-ar`; neither the device nor a CI worker
        carries that name, and the device has no plain `ar`/`ld` either —
        harmonybrew provides llvm-ar on PATH while the linker exists only as
        `<sdk>/native/llvm/bin/ld.lld`.  The OHOS profile declares these in its
        [env] section, but that section is applied only through conan's own
        runners and this recipe drives configure as a raw subprocess, so they
        are re-declared here: first by PATH, then next to the C compiler.
        Without them the probes degrade and automake/libtool aborts — observed
        on the device, in this order:
            configure: error: could not determine false interface      (no AR)
            configure: error: no acceptable ld found in $PATH          (no LD)
        """
        search_dirs = [os.path.dirname(str(cc)) for cc in
                       (self._compiler_environment_items().get("CC"),)
                       if cc]
        items = {}
        for variable, probes in _BINUTILS:
            for probe in probes:
                found = shutil.which(probe)
                if not found:
                    for directory in search_dirs:
                        candidate = os.path.join(directory, probe)
                        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                            found = candidate
                            break
                if found:
                    items[variable] = found
                    break
        return items

    def _compiler_environment_items(self):
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

        configure.ac checks REVENGE, XML, ZLIB, MDDS, CPPUNIT and — because
        both --enable-tests and --with-tools are on — REVENGE_STREAM and
        REVENGE_GENERATORS.  Each pair must have *both* halves non-empty:
        PKG_CHECK_MODULES short-circuits each half independently and an empty
        half falls through to pkg-config, which exists in this build
        environment and then fails the check with a hard as_fn_error
        (device-verified for mdds and revenge-generators).
        """
        revenge = self.dependencies["librevenge"].package_folder
        xml2 = self.dependencies["libxml2"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        boost_include = (
            f"-I{self.dependencies.build['boost'].package_folder}/include")
        glm_include = (
            f"-I{self.dependencies.build['glm'].package_folder}/include")
        mdds = self.dependencies.build["mdds"]
        cppunit = self.dependencies.build["cppunit"]
        revenge_include = f"-I{revenge}/include/librevenge-0.0"
        xml_include = f"-I{xml2}/include/libxml2 -I{xml2}/include"
        cppflags = " ".join(filter(None, [
            boost_include, glm_include, os.environ.get("CPPFLAGS", "")]))
        # mdds 3.0 headers use C++17 (std::bool_constant) while the project
        # asks for C++11 through AX_CXX_COMPILE_STDCXX_11, a macro that adds no
        # -std flag when the compiler default already satisfies C++11 (SDK
        # clang 15 defaults to gnu++14) — pin the profile's cppstd explicitly.
        cxxflags = " ".join(filter(None, [
            "-std=c++17", os.environ.get("CXXFLAGS", "")]))
        link = f"-L{self._clean_link_dir()}"
        xml_link = f"-L{xml2}/lib"
        zlib_link = f"-L{zlib}/lib"
        # Bake the shared libraries' directories into RUNPATH so `make check`
        # and the installed converters resolve libxml2.so at run time without
        # this recipe ever exporting LD_LIBRARY_PATH (which breaks lld).
        rpath = f"-Wl,-rpath,{xml2}/lib -Wl,-rpath,{zlib}/lib"
        return {
            "BOOST_CFLAGS": boost_include,
            "CPPFLAGS": cppflags,
            "CXXFLAGS": cxxflags,
            "GLM_CFLAGS": glm_include,
            "MDDS_CFLAGS": f"-I{mdds.package_folder}/include/mdds-3.0",
            "MDDS_LIBS": f"-L{mdds.package_folder}/lib",
            "CPPUNIT_CFLAGS": f"-I{cppunit.package_folder}/include",
            "CPPUNIT_LIBS": f"-L{cppunit.package_folder}/lib -lcppunit",
            "REVENGE_CFLAGS": revenge_include,
            "REVENGE_LIBS":
                f"{link} -lrevenge-0.0 {xml_link} -lxml2 {zlib_link} -lz "
                f"{rpath} -lm",
            "REVENGE_GENERATORS_CFLAGS": revenge_include,
            "REVENGE_GENERATORS_LIBS":
                f"{link} -lrevenge-generators-0.0 -lrevenge-0.0 "
                f"{xml_link} -lxml2 {zlib_link} -lz {rpath} -lm",
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
        """Directory holding the librevenge archives and no `.la` file.

        libtool resolves -l<name> by preferring a matching `.la` among the -L
        directories, and a dependency's `.la` records the libdir it was
        installed for (`//lib`, since these recipes use prefix=/ plus DESTDIR),
        which turns a cross-package link into "cannot find the library
        '//lib/librevenge-0.0.la'".  A directory with only the archives keeps
        libtool on the plain -L/-l path.
        """
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
        return str(clean)

    def _resolve_shell(self):
        for candidate in _ohos_shell_candidates():
            if os.path.sep in candidate:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
                continue
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                path = os.path.join(directory, candidate)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
        raise ConanInvalidConfiguration(
            "no suitable shell found on OHOS (need the hnp bash or zsh; zsh "
            "cannot run automake's recursive make)")

    def _run_ohos(self, command, cwd=None):
        shell = self._resolve_shell()
        environment = dict(os.environ)
        environment["SHELL"] = shell
        environment["CONFIG_SHELL"] = shell
        import subprocess
        completed = subprocess.run(command + " < /dev/null", shell=True,
                                   env=environment, cwd=cwd or self.build_folder,
                                   stdin=subprocess.DEVNULL)
        if completed.returncode != 0:
            self._dump_failure_diagnostics(cwd or self.build_folder, environment)
            raise ConanException(
                f"OHOS build step failed (rc={completed.returncode}): {command}")

    def _dump_failure_diagnostics(self, directory, environment):
        """Print the environment and config.log into the captured build log.

        A CI worker's log is the only observation point this recipe gets on that
        fleet, and a bare "configure: error: C compiler cannot create
        executables" says nothing about which TMPDIR/LD_LIBRARY_PATH/PATH the
        compiler test actually saw.
        """
        self.output.info("---- ohos diagnostics: environment ----")
        for name in ("CC", "CXX", "CPPFLAGS", "LDFLAGS", "LIBS", "CFLAGS",
                     "CXXFLAGS", "TMPDIR", "LD_LIBRARY_PATH"):
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
            "cacert, $CONAN_HOME/cacert.pem and $SSL_CERT_FILE")

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
