#!/usr/bin/env python3
"""Conan recipe for PRANK 250331 — HarmonyOS PC (OpenHarmony) aarch64 adaptation.

Upstream homepage: https://ariloytynoja.github.io/prank-msa/
Upstream source:   https://github.com/ariloytynoja/prank-msa

PRANK is a probabilistic multiple-sequence-alignment engine (DNA/RNA/protein/
codon) that models insertions and deletions along the tree instead of treating
gaps as missing data.

Build system: a single hand-written Makefile in ``src/`` with no
configure/cmake/meson layer, so everything the toolchain needs has to be
injected as make-variable overrides on the command line.

OHOS adaptations (each one verified individually, see notes.md):
1. ``CC=gcc`` / ``CXX=g++`` / ``LINK=g++`` are baked into the Makefile. The
   OHOS SDK ships only clang and neither gcc nor g++ exists on the worker, so
   the compilers are read from the Conan conf
   ``tools.build:compiler_executables`` and passed as make overrides
   (R33 — never from raw shell ``$CC``/``$CXX``).
2. ``CFLAGS``/``CXXFLAGS`` carry ``-m64`` (x86-64 only) and ``LFLAGS=-m64`` is
   used at link time; both are rebuilt from ``build_type`` instead.
3. ``INCPATH = -I. -I/usr/include`` points at the *build host's* /usr/include,
   which is not the OHOS sysroot. Reduced to ``-I.`` — every PRANK header is
   included relative to ``src/``.
4. ``install:``/``uninstall:`` are empty ``FORCE`` rules: upstream has no
   install logic at all, so ``package()`` places the binary and man page.
5. Upstream's default goal is ``all: Makefile $(TARGET) $(MANPAGES)`` and
   ``$(MANPAGES)`` is rebuilt from ``prank.1.pod`` through ``pod2man``. The
   compile step therefore targets the ``prank`` binary directly, keeping perl
   out of the critical path; the man page ships pre-rendered in the upstream
   snapshot and is taken along as-is.
6. ``-j1``: the OHOS make wrapper exposes no jobserver, and parallel make only
   interleaves compiler diagnostics.

Runtime dependencies: none. The external aligners PRANK can call (mafft,
exonerate, bppancestor, raxmlHPC) are optional helper programs used only by the
corresponding command-line options; the default DNA/protein alignment path, the
guide-tree writer and the format converter are fully self-contained.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class PrankConan(ConanFile):
    name = "prank"
    version = "250331"
    description = ("PRANK - probabilistic multiple sequence alignment engine "
                   "with an explicit model of insertions and deletions")
    license = "GPL-2.0-or-later"
    homepage = "https://ariloytynoja.github.io/prank-msa/"
    url = "https://github.com/ariloytynoja/prank-msa"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: the platform test must stay open for Linux build hosts too.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "prank is only validated for Linux/OHOS, not %s"
                % self.settings.os)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── toolchain plumbing ─────────────────────────────────────────────
    def _compilers(self):
        """Absolute compiler paths read from the Conan conf (R33).

        ``tools.build:compiler_executables`` is what the ohos-aarch64 profile
        fills in; falling back to a bare ``clang++`` name would silently pick
        whatever the worker PATH happens to expose.
        """
        conf = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        cxx = (conf.get("cpp") or conf.get("c") or "").strip()
        cc = (conf.get("c") or "").strip()
        if not cxx or not os.path.isfile(cxx):
            raise ConanInvalidConfiguration(
                "no usable C++ compiler: conf "
                "tools.build:compiler_executables yielded %r; refusing to "
                "build prank with an unvalidated compiler" % (cxx,))
        return cc or cxx, cxx

    def _flags(self):
        # Upstream hard-codes "-m64 -pipe -O3"; -m64 is x86-64 only and -pipe
        # is noise here, so the value is rebuilt from build_type instead.
        if str(self.settings.build_type) == "Release":
            return "-O3 -DNDEBUG"
        return "-O0 -g"

    def _src_dir(self):
        # strip_root=True yields <source_folder>/{VERSION_HISTORY,src/}
        src = os.path.join(self.source_folder, "src")
        if not os.path.isfile(os.path.join(src, "Makefile")):
            raise ConanInvalidConfiguration(
                "upstream Makefile not found under %s" % src)
        return src

    def build(self):
        apply_conandata_patches(self)
        cc, cxx = self._compilers()
        src = self._src_dir()
        flags = self._flags()
        defines = "-DNDEBUG" if str(self.settings.build_type) == "Release" else ""
        self.output.info("prank: compiling with CXX=%s flags=%s" % (cxx, flags))
        overrides = [
            # All eight variables are assigned inside the Makefile; a
            # command-line override wins, so no patch is needed to get the
            # right compiler, flags and include path (R1: minimal parameters).
            'CC="%s"' % cc,
            'CXX="%s"' % cxx,
            'LINK="%s"' % cxx,
            'DEFINES=%s' % defines,
            'CFLAGS="%s"' % flags,
            'CXXFLAGS="%s"' % flags,
            'INCPATH="-I."',
            'LFLAGS=',
        ]
        # `prank` is the binary on its own. Upstream's default goal `all`
        # additionally regenerates prank.1 via pod2man — a documentation step
        # that must not gate the build (see module docstring, point 5).
        self.run(" ".join(["make", "-j1", "-C", '"%s"' % src] + overrides
                          + ["prank"]),
                 env="conanbuild")

    def package(self):
        src = self._src_dir()
        binary = os.path.join(src, "prank")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                "build produced no prank binary under %s" % src)
        copy(self, "prank", src=src,
             dst=os.path.join(self.package_folder, "bin"))
        # Shipped pre-rendered inside the upstream snapshot; no pod2man needed.
        copy(self, "prank.1", src=src,
             dst=os.path.join(self.package_folder, "man", "man1"))
        exe = os.path.join(self.package_folder, "bin", "prank")
        try:
            os.chmod(exe, 0o755)
        except OSError:
            # HMDFS ignores chmod (E046). The file already carries the mode the
            # linker produced, so this is not fatal.
            self.output.warning(
                "prank: chmod 755 on the packaged binary was ignored")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Application package: nothing to link against, no headers, no libs.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.frameworks = []
        self.cpp_info.system_libs = []
