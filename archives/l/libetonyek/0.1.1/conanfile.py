#!/usr/bin/env python3
"""Conan recipe for libetonyek 0.1.1 — Apple iWork document parser library.

libetonyek parses Apple iWork documents (Keynote/Pages/Numbers) and feeds
them to librevenge generators.  This is the 2013-era first stable release:
the source layout is the pre-IWA `KEY*` family (KEY1/KEY2 parsers for the
old XML-based Keynote format, PAG*/NUM* for Pages and Numbers), a full
cppunit suite in src/test/ (KEY2Token, KEYOutput, KEYPath, KEYPropertyMap,
KEYShape, KEYStyleContext, KEYStyles, KEYTransformation, KEYXMLReader), and
the conversion tools key2raw/key2text/key2xhtml/numbers2csv/numbers2raw/
numbers2text/pages2html/pages2raw/pages2text under src/conv/.

Dependency surface of 0.1.1 (configure.ac, far smaller than 0.1.13's):

* librevenge-0.0 (+ librevenge-generators-0.0 / librevenge-stream-0.0 when
  the conversion tools are enabled, which they are by default)
* libxml-2.0 and zlib — only through their stable xmlReader / inflate APIs,
  so the platform's libxml2 2.15.x works unpatched (the "old code vs new
  libxml2" compatibility probe came back clean: the single use of
  xmlReaderForIO and the xmlTextReader* family is ABI-stable since 2.6).
* boost headers only (spirit classic, any, function, lexical_cast, optional,
  scoped_ptr, shared_ptr, unordered_map) — header-only, private to the
  translation units, hence tool_requires.
* cppunit when --enable-tests (default yes).
* the gperf code generator: Token .inc files are NOT in the dist tarball,
  src/lib/Makefile.am regenerates KEY{1,2}Token.inc / NUMToken.inc /
  PAGToken.inc from .gperf at build time.  The OHOS toolchain (hnp) ships
  gperf 3.1, so this works natively; no emulation is needed.

No mdds, no glm, no liblangtag in this version — those entered the
dependency tree later (0.1.13 needs all three).

Build system: autotools with a dist-carried `configure` (GNU Autoconf
2.69), so no autoreconf is needed — the OHOS device has no automake/
libtoolize.  The dist's config.guess/config.sub are the 2012-12-29
old-style scripts: they do not know HarmonyOS/ohos, and the repo's
patch-autotools-ohos.pl anchors miss the old-style code (DRAFT-E564), so a
hand-anchored portability patch (patches/0001) re-anchors both scripts —
config.guess learns `aarch64:HarmonyOS:*:*` → aarch64-unknown-linux-ohos
and config.sub accepts the linux-ohos kernel-libc pair in both of its two
matching sites (the maybe_os kernel split and the basic os list).

Every PKG_CHECK_MODULES call in configure.ac needs *both* of its
`<PREFIX>_CFLAGS` and `<PREFIX>_LIBS` exported, and neither may be empty:
the macro short-circuits each half independently, and an empty half falls
through to pkg-config — which exists in the build environment and then
fails the check with a hard `as_fn_error`.  This configure checks REVENGE,
XML, ZLIB, CPPUNIT, REVENGE_GENERATORS and REVENGE_STREAM (six pairs).

OHOS machinery (carried over from this author's libetonyek 0.1.13 /
libwpd / libcaca ports, each item re-probed against this tarball first):

* **Compilers pinned from the profile.**  conan's AutotoolsToolchain writes
  CC/CXX into conanautotoolstoolchain.sh, but that script is sourced only
  by conan's own Autotools() helper; a raw subprocess never sees it.  Left
  unset, autoconf falls back to a bare `clang` from PATH that cannot link
  OHOS executables ("C compiler cannot create executables", libetonyek CI
  #47165/#48068).
* **Shell**: `/data/service/hnp/bin/bash`.  toybox `/system/bin/sh` rejects
  the `exec 7<&0` fd-redirect in autoconf's configure; bash also gives the
  POSIX IFS word splitting automake's recursive make needs.
* **umask 077 -> 022** in the generated configure: its scratch directory is
  created with `umask 077` (mode 2700) and hmdfs decides traversal on the
  group bits, where `chmod` has no effect — the directory becomes
  untraversable and everything inside it fails with EACCES.
* **Triplets**: after the re-anchor patch this dist's config.sub accepts
  `aarch64-unknown-linux-ohos` natively, so the plain pair below works and
  keeps build != host (cross mode; configure never runs what it compiles).
* **In-tree build**: the source tree is copied into the build folder before
  configuring, as in the sibling recipes in this archive.

Upstream's own suite runs as a hard gate: `make check` in build() executes
the cppunit `test` binary (single TESTS entry aggregating the nine KEY*
test suites).
"""

import hashlib
import os
import shlex
import ssl
import subprocess
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


class LibetonyekConan(ConanFile):
    name = "libetonyek"
    version = "0.1.1"
    description = ("Library for parsing Apple iWork documents through the "
                   "librevenge document model")
    license = "MPL-2.0"
    homepage = "https://wiki.documentfoundation.org/Development/libetonyek"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("librevenge/0.0.5")
        # The 0.1.1 public header includes librevenge-stream types
        # (EtonyekDocument.h includes librevenge-stream/librevenge-stream.h),
        # and the library links libxml2 + zlib directly (src/lib/Makefile.am
        # LIBADD carries $(XML_LIBS) $(ZLIB_LIBS)).
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # Header-only, used by libetonyek's own translation units only —
        # boost appears in neither the public headers (inc/) nor the link
        # interface, so it must not appear in cpp_info.requires.  0.1.1 uses
        # spirit *classic* (boost/spirit/include/classic_core.hpp in
        # KEYPath.cpp), which the platform boost 1.90.0.3 still ships.
        self.tool_requires("boost/1.90.0.3")
        # Upstream's cppunit suite is built with --enable-tests (default on).
        self.tool_requires("cppunit/1.15.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libetonyek is adapted for Linux and OHOS, not "
                f"{self.settings.os}"
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
        archive = Path(self.source_folder, "libetonyek-source.tar.xz")
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
        self.cpp_info.set_property("cmake_file_name", "libetonyek")
        self.cpp_info.set_property("cmake_target_name", "libetonyek::libetonyek")
        self.cpp_info.set_property("pkg_config_name", "libetonyek-0.1")
        self.cpp_info.libs = ["etonyek-0.1"]
        # 0.1.1 installs headers to include/libetonyek-0.1/libetonyek/ (the
        # versioned include dir keeps the libetonyek/ subdirectory), so
        # consumers include <libetonyek/EtonyekDocument.h>.
        self.cpp_info.includedirs = ["include/libetonyek-0.1"]
        self.cpp_info.requires = ["librevenge::librevenge",
                                  "libxml2::libxml2", "zlib::zlib"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            # build != host keeps configure in cross mode.  After the
            # 0001 re-anchor patch the dist's 2012 config.sub accepts
            # aarch64-unknown-linux-ohos natively (verified on device:
            # config.guess -> aarch64-unknown-linux-ohos, config.sub echoes
            # it back unchanged).
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-ohos",
            "--prefix=/",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--disable-dependency-tracking",
            # --enable-tests is the default, but spelled out here because
            # the recipe's hard gate (make check in build()) depends on it.
            "--enable-tests",
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
            # R34/R51: upstream's own suite — src/test/ registers the
            # cppunit aggregate `test` in both check_PROGRAMS and TESTS, so
            # `make check` runs it (needs --enable-tests).  A failure fails
            # the build.
            self._run_ohos("make -j1 check")

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again (E490)."""
        candidates = [
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ltmain.sh", "config.status",
            "ar-lib", "mkinstalldirs", "test-driver",
        ]
        for relative in candidates:
            path = Path(self.build_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)

    def _relax_umask_in_configure(self):
        """Rewrite `umask 077` -> `umask 022` in the generated configure.

        Device-verified (ncrack, libcaca, libcdaudio, libetonyek 0.1.13):
        the scratch dir is created with `umask 077` giving mode 2700, and
        hmdfs decides traversal on the group bits where `chmod` is a no-op,
        so the directory is untraversable (EACCES on everything inside it).
        022 yields `drwxr-s--x`.
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
        # (CI-021 build #48068).  An explicit empty value shields the
        # compiler chain from any ambient loader path on every worker.
        environment.define("LD_LIBRARY_PATH", "")
        # The just-built test programs still have to find the versioned
        # shared libxml2 at run time; that lookup is solved by baking
        # -Wl,-rpath into their link line (see _dependency_environment_items),
        # which lld honours at link time without touching the loader path
        # the compiler drives.
        for name, value in self._compiler_environment_items().items():
            environment.define(name, value)
        for name, value in self._dependency_environment_items().items():
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

    def _dependency_environment_items(self):
        """<PREFIX>_CFLAGS/_LIBS for every PKG_CHECK_MODULES call in this
        configure.ac, plus the boost include path the sources need.

        configure.ac checks six module pairs — REVENGE, XML, ZLIB, CPPUNIT
        and (because the tools are enabled by default) REVENGE_GENERATORS /
        REVENGE_STREAM — and the device has no usable pkg-config for the
        conan packages, so each check is satisfied by handing it the
        variable pair it would otherwise ask pkg-config for;
        PKG_CHECK_MODULES uses those verbatim when the CFLAGS half is
        non-empty, and the LIBS half must never be empty either (see the
        module docstring).  Every `*_LIBS` also carries the transitive
        archives the static dependencies need (zlib for librevenge's
        stream layer, libm for libxml2).

        0.1.1 needs no MDDS/GLM/LANGTAG variables — those dependencies do
        not exist in this version (they entered later), which also means
        the C++17 pinning of 0.1.13 (mdds 3.0 headers) is unnecessary
        here: 0.1.1 compiles happily as the pre-C++11-aware C++ the
        configure.ac of 2013 set out to build, and the SDK clang's default
        gnu++14 mode accepts all of it.

        Dependency libraries are referenced through a directory that holds
        only the archives, never libtool `.la` files — see `_clean_link_dir`.
        """
        revenge = self.dependencies["librevenge"].package_folder
        xml2 = self.dependencies["libxml2"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        boost_include = (
            f"-I{self.dependencies.build['boost'].package_folder}/include")
        cppunit = self.dependencies.build["cppunit"]
        revenge_include = f"-I{revenge}/include/librevenge-0.0"
        xml_include = f"-I{xml2}/include/libxml2 -I{xml2}/include"
        ambient = os.environ.get("CPPFLAGS", "")
        cppflags = " ".join(filter(None, [boost_include, ambient]))
        # librevenge ships libtool `.la` files, so it goes through the clean
        # directory; libxml2/zlib are packaged without them (and libxml2 is
        # a versioned shared library, which must not be copied around).
        link = f"-L{self._clean_link_dir()}"
        xml_link = f"-L{xml2}/lib"
        zlib_link = f"-L{zlib}/lib"
        # Bake the shared libraries' directories into every program's
        # RUNPATH so `make check` resolves libxml2.so.16 at run time without
        # this recipe ever having to set LD_LIBRARY_PATH (which breaks lld —
        # see _build_environment).  musl honours DT_RUNPATH.
        rpath = f"-Wl,-rpath,{xml2}/lib -Wl,-rpath,{zlib}/lib"
        return {
            "BOOST_CFLAGS": boost_include,
            "CPPFLAGS": cppflags,
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
            "CPPUNIT_CFLAGS": f"-I{cppunit.package_folder}/include",
            "CPPUNIT_LIBS": f"-L{cppunit.package_folder}/lib -lcppunit",
        }

    def _clean_link_dir(self):
        """Directory holding the librevenge archives, and no `.la` file.

        libtool resolves `-l<name>` by looking for a matching `.la` in the
        `-L` directories first, and the `.la` shipped by a dependency
        records the libdir it was installed for (`//lib`, because the
        recipes use prefix=/ plus DESTDIR).  That makes a cross-package
        link fail with

            libtool: warning: library '.../librevenge-0.0.la' was moved.
            libtool: error: cannot find the library '//lib/librevenge-0.0.la'

        (device-verified on libwpd).  Naming the archives by absolute path
        instead makes libtool treat them as input *members* and archive
        them into the produced static library, which clashes with the same
        library linked by a consumer.  Linking against a directory that
        contains only the archives keeps libtool on the plain `-L/-l` path.
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
        that fleet, and a bare `configure: error: ...` says nothing about
        which value TMPDIR/LD_LIBRARY_PATH/PATH actually had when the
        compiler test ran, nor what config.log recorded of the clang
        invocation.  Print both so the next diagnosis runs on facts.
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
