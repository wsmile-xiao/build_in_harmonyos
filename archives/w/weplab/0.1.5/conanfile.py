#!/usr/bin/env python3
"""Conan recipe for weplab 0.1.5 — WEP key cracker.

weplab is a CLI tool for teaching WEP wireless encryption vulnerabilities:
packet capture/analysis from pcap files and key cracking via FMS, Korek,
dictionary and brute-force attacks.  Build system is autotools
(``configure.ac`` + ``Makefile.am``) producing a single ``weplab`` binary
that links against libpcap.  It has no upstream test suite —
``make check`` resolves to ``check-am: all-am`` with no test harness —
so the MANIFEST.yml and shell consumer tests document this explicitly.

Platform issues resolved (see notes.md and patches/):

* The upstream configure.ac has gcc-version-specific optimization flag blocks
  that fall through a chain of ``$CC -dumpversion`` regexes.  On OHOS the
  compiler is Clang (which still understands ``-dumpversion`` but reports a
  version like ``15.0.0`` that matches none of the branches), so configure
  takes the ``warning: compiler is not known`` fallback and applies NO
  special CFLAGS.  That's safe — but the subsequent cpuinfo-based ``-march``
  and ``-msse`` flags generated in the gcc-3.x branch are x86-only and must
  be suppressed for aarch64.  The patch replaces the entire arch-specific
  flag block with a single empty MARCH variable.
* configure.ac's ``AC_CHECK_LIB(pcap, pcap_open_live, ...)`` stops configure
  with "ERROR: You need libpcap-dev!" when the library isn't found — but
  Conan 2.29's AutotoolsToolchain doesn't pass ``-I``/``-L`` flags from
  dependencies (E430).  The recipe works around this in ``build()`` by
  passing ``CFLAGS``/``LDFLAGS``/``LIBS`` explicitly to configure,
  pointing at the real libpcap package folders (never at the shared
  system prefix — R49/E524).
* configure runs ``autoconf``/``automake`` during normal flow via the
  ``config.status: configure`` rule, but the OHOS sandbox (HMDFS + execve
  restrictions) cannot execve scripts from the source tree.  The recipe
  runs autotools from the recipe context (bundle python invokes perl/sh
  directly — see references/build-systems.md autotools bootstrap
  convention) and delivers a pre-bootstrapped ``configure`` script so
  the build directory never invokes autoreconf.
* config.status creates its scratch directory with ``mktemp -d`` under
  ``umask 077`` — the directory is hardwired to mode 0700.  On native
  filesystems the owner can still write, but on HMDFS/FUSE mounts (CI
  workers keep the conan cache under /storage) chmod is ignored and
  ownership is remapped, so the 0700 directory is unwritable and
  Makefile generation dies with ``can't create ./confstat*/subs.sed:
  Permission denied``.  The recipe repairs the generated config.status
  to create the directory world-traversable at creation time (umask
  022 + plain mkdir — chmod cannot repair it on FUSE, same lesson as
  E490) and re-runs config.status when the Makefile is missing.

Dependency graph: a single leaf dependency, ``libpcap/1.10.6`` from the
ohpcd registry.  The product is a single executable, so this recipe is
``package_type = application``: it exports no ``cpp_info.libs`` and is
registered for the platform command index by
``archives/w/weplab/commands.json`` (R38).
"""

import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WeplabConan(ConanFile):
    name = "weplab"
    version = "0.1.5"
    description = "WEP protocol teaching and key-cracking tool (pcap-based, libpcap)"
    license = "GPL-2.0-or-later"
    homepage = "https://weplab.sf.net"
    url = "https://weplab.sf.net"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "libpcap/1.10.6",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"weplab requires libpcap on Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        # E430 / R49: Conan 2.29's AutotoolsToolchain does not forward
        # dependency -I/-L flags, so the pcap.h header and -lpcap library
        # would not be discoverable by configure / make.  We rely on
        # AutotoolsDeps to generate conanbuildenv.sh with CPPFLAGS/LDFLAGS
        # that are picked up by the conanbuild buildenv, and supplement
        # them in build() with explicit -I/-L/-l flags pointing at the
        # real package folders (never at the shared system prefix —
        # R49/E524).
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # E490 / restore-known-autotools-script-modes: some OHOS adaptation
        # paths preserve source content without the executable bit, which
        # breaks ./configure and the automake-1.4 helper scripts.  Restore
        # the conventional modes explicitly after patching.
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "mkinstalldirs"):
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                os.chmod(path, 0o755)
        # E430: AutotoolsDeps generates conanbuildenv.sh with CPPFLAGS/LDFLAGS
        # from the dependency tree.  These are picked up by the conanbuild
        # environment when running configure/make.  We also pass -lpcap via
        # LIBS to ensure AC_CHECK_LIB(pcap, ...) succeeds.
        pcap_dep = self.dependencies["libpcap"]
        pcap_inc = os.path.join(pcap_dep.package_folder, "include")
        pcap_lib = os.path.join(pcap_dep.package_folder, "lib")
        # Run configure with explicit flags so AC_CHECK_LIB(pcap, ...) finds
        # the Conan-managed libpcap.  The upstream configure script is pre-
        # bootstrapped in the tarball (no autoreconf needed).
        # Use subshell with exec 0</dev/null to avoid `cat -` / `sort -`
        # failures in config.status when stdin is not available in
        # the conan subprocess environment.
        cmd = (
            f'CFLAGS="-I{pcap_inc}" LDFLAGS="-L{pcap_lib}" LIBS="-lpcap" '
            f'./configure --prefix=/ '
            f'--build=aarch64-linux-ohos --host=aarch64-linux-ohos'
        )
        subprocess.run(
            ['sh', '-c', f'exec 0</dev/null && {cmd}'],
            cwd=self.source_folder,
            env={**os.environ, 'PATH': os.environ.get('PATH', '')},
            stdin=subprocess.DEVNULL,
        )
        # config.status scratch-dir permission repair (see docstring):
        # when the generated Makefile is missing — which happens on
        # HMDFS/FUSE caches where config.status's `mktemp -d` 0700 temp
        # directory is unwritable — rewrite config.status to create its
        # scratch directory mode 0755 at creation time and re-run it.
        makefile_path = os.path.join(self.source_folder, "Makefile")
        if not os.path.exists(makefile_path):
            self._fix_config_status_tmpdir(
                os.path.join(self.source_folder, "config.status"))
            subprocess.run(
                ['sh', '-c', 'exec 0</dev/null && ./config.status'],
                cwd=self.source_folder,
                stdin=subprocess.DEVNULL,
            )
            if not os.path.exists(makefile_path):
                raise ConanException(
                    "config.status did not generate Makefile after "
                    "scratch-dir permission repair")
        # weplab uses automake 1.4-p6 which requires in-tree build.
        # `make` triggers `config.status --recheck` (because `missing` reports
        # aclocal-1.4/automake-1.4 missing), which re-runs configure and
        # fails on `cat -` in the OHOS sandbox.  Bypass make and compile
        # directly from the generated Makefile's compile commands.
        with open(makefile_path, "r") as f:
            makefile = f.read()
        # Extract compiler, flags, LIBS, object list from Makefile
        cc = re.search(r'^CC\s*=\s*(.*)', makefile, re.MULTILINE).group(1).strip()
        cflags = re.search(r'^CFLAGS\s*=\s*(.*)', makefile, re.MULTILINE).group(1).strip()
        libs = re.search(r'^LIBS\s*=\s*(.*)', makefile, re.MULTILINE).group(1).strip()
        ldflags = re.search(r'^LDFLAGS\s*=\s*(.*)', makefile, re.MULTILINE).group(1).strip() if re.search(r'^LDFLAGS\s*=', makefile, re.MULTILINE) else ""
        # Find .c source files from weplab_SOURCES
        sources_match = re.search(r'weplab_SOURCES\s*=\s*(.*)', makefile, re.MULTILINE)
        if sources_match:
            sources = [s for s in sources_match.group(1).split() if s.endswith('.c')]
        else:
            sources = []
        # Compile each source to object, then link
        # Use -std=gnu89 to handle the upstream's inline function semantics
        # (debug() in debug.h, IncrementKeyOptimized() in bruteforce.c are
        # inline functions called across translation units; gnu89 mode
        # generates external-linkable symbols, matching gcc's default behavior).
        obj_dir = os.path.join(self.source_folder, ".ohos-obj")
        os.makedirs(obj_dir, exist_ok=True)
        objects = []
        for src in sources:
            obj = os.path.join(obj_dir, os.path.basename(src).replace('.c', '.o'))
            self.run(f"{cc} -std=gnu89 {cflags} -c {src} -o {obj}", cwd=self.source_folder, env="conanbuild")
            objects.append(obj)
        # Link the binary.  The upstream code has duplicate global variable
        # definitions across multiple .c files (actualTime/initialTime/lastTime
        # in bruteforce.c, heuristics.c, dictionary.c, capture.c).  Old gcc
        # defaulted to -fcommon which tolerates this; lld on OHOS is stricter.
        # Use --allow-multiple-definition to match the original toolchain
        # behavior (R21: preserve upstream semantics where possible).
        self.run(f"{cc} {ldflags} {' '.join(objects)} {libs} -Wl,--allow-multiple-definition -o weplab", cwd=self.source_folder, env="conanbuild")

    @staticmethod
    def _fix_config_status_tmpdir(config_status_path):
        """Rewrite config.status's secure-tmpdir creation for FUSE caches.

        Upstream (autoconf 2.59-era template) creates its scratch directory
        with ``(umask 077 && mktemp -d -q "./confstatXXXXXX")`` — ``mktemp
        -d`` hardwires mode 0700.  On native filesystems the owner can
        still write inside it, but on HMDFS/FUSE mounts chmod is ignored
        and ownership is remapped, so the 0700 directory is unwritable and
        every file creation inside it fails with ``Permission denied``
        (subs.sed, subs.frag, out — i.e. the Makefile is never produced).

        Replace the mktemp invocation and the umask-077 mkdir fallback so
        the directory is created world-traversable (0755) at creation
        time.  Only the creation mode matters: chmod cannot repair this
        on FUSE (E490 lesson).  The directory name stays PID/RANDOM-based
        so a stale 0700 directory left by a failed earlier run never
        collides.
        """
        if not os.path.exists(config_status_path):
            return
        with open(config_status_path, "r") as f:
            text = f.read()
        text = text.replace(
            '(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null',
            '(umask 022 && d="./confstat$$-$RANDOM" && mkdir "$d" '
            '2>/dev/null && echo "$d") 2>/dev/null',
        )
        text = text.replace(
            "(umask 077 && mkdir $tmp)",
            "(umask 022 && mkdir $tmp)",
        )
        with open(config_status_path, "w") as f:
            f.write(text)

    def package(self):
        copy(
            self,
            "weplab",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "weplab.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )

    def package_info(self):
        # Standalone CLI tool: no libraries are exported.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
