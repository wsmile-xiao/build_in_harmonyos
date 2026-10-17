#!/usr/bin/env python3
"""Conan recipe for libabw 0.1.4 — AbiWord document parser library.

libabw parses AbiWord documents.  It is a sibling of libwpd/libwps in the
librevenge family but, unlike them, does not depend on libwpd at all —
verified against this tarball: configure.ac checks librevenge, libxml2 and
zlib, and neither the library nor the conversion tools reference libwpd.
Build system is autotools with a dist-carried `configure` (GNU Autoconf
2.72), so no autoreconf is needed — the OHOS device has no
automake/autoconf/libtoolize.

Dependency wiring: libwpd finds librevenge with
`PKG_CHECK_MODULES([REVENGE], [librevenge-0.0 >= 0.0.1])`, and — because
`--enable-tools` defaults to *yes* and the conversion tools need more of the
same package — two more checks for `librevenge-generators-0.0` and
`librevenge-stream-0.0`.  The device has no pkg-config, so the three
`<PREFIX>_CFLAGS`/`<PREFIX>_LIBS` variable pairs are exported from the
package folder instead; PKG_CHECK_MODULES prefers those over pkg-config by
design.  librevenge is a static library, so the link line also needs its own
dependency (zlib) — the `-lz` is carried in each variable pair rather than
left implicit.

OHOS machinery (carried over from this author's libcaca / libcdaudio ports,
each item re-probed against this tarball first):

* **Compilers pinned from the profile.**  conan's AutotoolsToolchain writes
  `CC`/`CXX` into conanautotoolstoolchain.sh, but that script is sourced only
  by conan's own Autotools() helper; a raw subprocess never sees it.  Left
  unset, autoconf falls back to a bare `clang` from PATH — the hnp toolchain
  on the device, but something that cannot link OHOS executables on a CI
  worker ("C compiler cannot create executables", libcdaudio CI #46506).
* **Shell**: `/data/service/hnp/bin/bash`.  This configure (autoconf 2.69)
  does contain `exec 7<&0`, which toybox `/system/bin/sh` rejects; bash also
  gives the POSIX IFS word splitting automake's recursive make needs (zsh
  does not, and zsh must never be the recipe shell for automake trees).
* **umask 077 -> 022** in the generated configure: its scratch directory is
  created with `umask 077` (mode 2700) and hmdfs decides traversal on the
  group bits, where `chmod` has no effect — the directory becomes
  untraversable and everything inside it fails with EACCES.
* **Triplets**: this dist's `config.sub` is dated 2012-02-10.  It knows
  `aarch64` but still not `musl`, so `aarch64-…-musl` is rejected while a
  four-part name carrying the `unknown` vendor passes through; the pair below
  keeps build != host, i.e. cross mode, and nothing here branches on
  build_cpu.
* **In-tree build**: the source tree is copied into the build folder before
  configuring, as in the other recipes in this archive.

Upstream ships no test suite (no `TESTS`/`check_PROGRAMS`, no test sources,
no `src/test/`), so test_package/ carries the verification: it builds a
document through librevenge's API, feeds it to libwpd's parser and asserts on
the callbacks it fires.
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
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, unzip)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class LibabwConan(ConanFile):
    name = "libabw"
    version = "0.1.4"
    description = "Library for reading and writing AbiWord documents"
    license = "LGPL-2.1-or-later OR MPL-2.0"
    homepage = "https://wiki.documentfoundation.org/Development/libabw"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("librevenge/0.0.5")
        # libabw's .pc names librevenge-0.0 + librevenge-stream-0.0 as public
        # requirements and libxml-2.0 + zlib as private ones.  All four end up
        # on the link line here because the dependencies are static.
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1")
        # libwpd itself compiles src/lib/libwpd_internal.cpp, which includes
        # <boost/spirit/include/qi.hpp>, and its configure.ac hard-errors with
        # "Required boost headers not found." when the header is missing.
        # Build-time only: the header is used by libwpd's own translation
        # units, it appears in neither libwpd's public headers nor its link
        # interface — so it must not be declared in cpp_info.requires, and
        # conan rejects a direct requirement that no component references.
        # The version is pinned to the one librevenge already depends on, so
        # the graph never wants two different boosts.
        self.tool_requires("boost/1.90.0.3")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libwpd is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official LibreOffice release tarball.

        Explicit download rather than conan's get()/download(): the CA trust
        store is resolved from conan's own certifi or $CONAN_HOME/cacert.pem
        with a hard failure when neither exists (AGENTS.md §1.2), and a
        failing download reports its URL and HTTP status instead of a
        FileNotFoundError naming the destination.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "libabw-source.tar.xz")
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
        copy(self, "COPYING.MPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libabw")
        self.cpp_info.set_property("cmake_target_name", "libabw::libabw")
        self.cpp_info.set_property("pkg_config_name", "libabw-0.1")
        self.cpp_info.libs = ["abw-0.1"]
        self.cpp_info.includedirs = ["include/libabw-0.1"]
        # Each entry is "<conan package>::<component>", and for a dependency
        # that defines no components the whole package is addressed by
        # repeating its name.  Conan is strict about both halves: a bare
        # "libxml2" is read as an *internal component* ("to other internal
        # components that are not defined"), and the CMake target name
        # "LibXml2::LibXml2" is rejected because the package would have to be
        # called LibXml2 ("not a direct requirement of the recipe").
        self.cpp_info.requires = ["librevenge::librevenge",
                                  "libxml2::libxml2", "zlib::zlib"]

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            # build != host keeps configure in cross mode (configure never
            # runs the programs it compiles).  This dist's config.sub is dated
            # 2024-05-27 and knows both `aarch64` and `musl`, so the ordinary
            # pair works — unlike libwpd's 2012 config.sub, which rejects
            # `musl` and needs the four-part `unknown`-vendor workaround.
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--disable-dependency-tracking",
            # --enable-tools is upstream's default (yes); the conversion
            # tools are kept so no capability is dropped.  Docs and fuzzers
            # default to off and stay off (doxygen/libFuzzer are out of scope).
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

        Device-verified (ncrack, libcaca, libcdaudio): the scratch dir is
        created with `umask 077` giving mode 2700, and hmdfs decides
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
        # No LD_LIBRARY_PATH here, on purpose.  The OHOS SDK's lld links
        # libxml2 for itself, and the musl loader resolves NEEDED libraries
        # from LD_LIBRARY_PATH *before* the SDK's own rpath — so putting the
        # conan libxml2 package on it makes lld load that copy instead, and
        # conan's libxml2 does not export the LLVM-internal subset (xmlCopy-
        # Namespace, xmlNewDoc, ...) lld relocates against:
        #   Error relocating .../llvm/bin/lld: xmlCopyNamespace: symbol not found
        #   configure: error: C compiler cannot create executables
        # (device-reproduced and read from CI config.log via the failure
        # diagnostics, 2026-09-14).  This recipe runs no upstream tests in
        # build(), so nothing here needs a loader path: its consumer test
        # runs under conan's own conanrun environment instead.
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
        """<PREFIX>_CFLAGS/_LIBS for every PKG_CHECK_MODULES call, plus the
        boost include path libabw's own sources need.

        configure.ac checks four modules — librevenge, libxml-2.0, zlib and
        (because `--enable-tools` defaults to yes) librevenge-generators /
        librevenge-stream — and the device has no pkg-config, so each check is
        satisfied by handing it the variable pair it would otherwise ask
        pkg-config for; PKG_CHECK_MODULES uses those verbatim when the CFLAGS
        half is non-empty.  Every `*_LIBS` also carries the transitive
        archives the static dependencies need (zlib for librevenge's stream
        layer, libm for libxml2).

        All dependency libraries are referenced through a directory that holds
        only the archives, never libtool `.la` files — see `_clean_link_dir`.
        """
        revenge = self.dependencies["librevenge"].package_folder
        xml2 = self.dependencies["libxml2"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        boost_include = (
            f"-I{self.dependencies.build['boost'].package_folder}/include")
        revenge_include = f"-I{revenge}/include/librevenge-0.0"
        xml_include = f"-I{xml2}/include/libxml2 -I{xml2}/include"
        ambient = os.environ.get("CPPFLAGS", "")
        cppflags = " ".join(filter(None, [boost_include, ambient]))
        # Only librevenge needs the clean directory: it ships libtool `.la`
        # files (see _clean_link_dir).  libxml2 and zlib are packaged without
        # them, and libxml2 ships a *versioned shared* library, so it is
        # referenced by its own lib directory — copying it into the clean
        # directory would carry over the `libxml2.so` symlink without its
        # targets and leave a dangling link behind (device-verified).
        link = f"-L{self._clean_link_dir()}"
        xml_link = f"-L{xml2}/lib"
        zlib_link = f"-L{zlib}/lib"
        return {
            "BOOST_CFLAGS": boost_include,
            "CPPFLAGS": cppflags,
            "REVENGE_CFLAGS": revenge_include,
            "REVENGE_LIBS": f"{link} -lrevenge-0.0 {xml_link} -lxml2 {zlib_link} -lz -lm",
            "REVENGE_GENERATORS_CFLAGS": revenge_include,
            "REVENGE_GENERATORS_LIBS":
                f"{link} -lrevenge-generators-0.0 -lrevenge-0.0 "
                f"{xml_link} -lxml2 {zlib_link} -lz -lm",
            "REVENGE_STREAM_CFLAGS": revenge_include,
            "REVENGE_STREAM_LIBS":
                f"{link} -lrevenge-stream-0.0 -lrevenge-0.0 "
                f"{xml_link} -lxml2 {zlib_link} -lz -lm",
            "LIBXML_CFLAGS": xml_include,
            "LIBXML_LIBS": f"{xml_link} -lxml2 {zlib_link} -lz -lm",
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
        # Only the librevenge packages ship `.la` files; the loop is kept
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
        import subprocess
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
