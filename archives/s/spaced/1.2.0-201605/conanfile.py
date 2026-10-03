#!/usr/bin/env python3
"""Conan recipe for spaced 1.2.0-201605.

spaced is a single-binary command line tool of the Computer Biology department
of the Georg-August-Universitaet Goettingen: it compares DNA or protein
sequences alignment-free by counting inexact word matches over "spaced" seeds
(Leimeister et al., Bioinformatics 2014).

Upstream build system: none worth the name.  The whole tarball is nine files -
three translation units, three headers, COPYING, README and a 100-byte Makefile
whose ``all`` target hardcodes ``g++ -O3 -fopenmp -std=c++11`` and which has no
``install`` and no ``check`` target.  So build() drives clang++ directly and
package() picks the binary out of the build folder (same idiom as
archives/s/smem/1.5, which also has to hand-roll an install step).

Zero Conan dependencies: nothing but the OHOS NDK clang and its libc++/libomp.
OpenMP is not optional here - sort.h carries seven ``#pragma omp parallel for``
regions plus omp_get_thread_num()/omp_set_num_threads() calls, and the
``#pragma omp``-less build silently degrades to a wrong answer rather than to a
build error, so the flag is mandatory rather than an optimisation.

OHOS adaptation points (full write-up in notes.md):
  * 0001  Portability.  Three distinct things, only the first of which is
    libc++-specific:
      - ``<tr1/unordered_map>`` is a libstdc++-only header that libc++ does not
        ship (and that nothing in the tree uses).
      - ``std::default_random_engine`` needs an explicit ``<random>``: neither
        libc++ nor libstdc++ 11 pulls it in transitively (verified: g++ 11.4 on
        the pristine tree reports the same "does not name a type").
      - ``std::abs()`` applied to the ``uint32_t`` members inside ``if (x < 0)``
        blocks is ambiguous: the C library's ``int abs(int)`` and the C++
        overload set are both plain conversions from ``unsigned int``, and the
        signed-representability tiebreaker does not apply to an unsigned
        argument.  Verified to fail identically under g++ 11.4 + glibc, so this
        hunk is toolchain-independent rather than an OHOS quirk.  Those three
        branches are unreachable for unsigned members, so they are dropped -
        the same edit Debian carries in its 0004-signed / 0005-fix-absolute-
        value-of-unsigned quilt patches.
  * 0002  AAPCS64 makes plain ``char`` unsigned, and ``patternset::ReadPattern``
    stores ``ifstream::get()``'s ``int_type`` into a ``char``.  The EOF (-1)
    sentinel therefore becomes 0xff, ``-1 == (int)c`` stops matching, and every
    pattern file handed to ``spaced -f`` is rejected with
    "Pattern containes illegal characters!" before the tool silently falls back
    to a random seed set.  Keeping the stream's ``int_type`` fixes it at the
    source and keeps the behaviour identical on signed-char targets.
  * -static-openmp: upstream links the OpenMP runtime.  With the OHOS SDK's
    shared ``libomp.so`` the binary ends up with a DT_NEEDED on a library that
    is not in the OHOS loader's default search path (clang stamps RUNPATH
    ``/usr/lib/llvm-15/lib``, the host toolchain's resource dir), so the tool
    refuses to start with "Error loading shared library libomp.so".  Linking
    the static runtime leaves ``libc.so`` as the only dependency, i.e. a
    self-contained executable that the consumer test can actually run.
    Precedent for OHOS having a usable libomp at all:
    archives/a/aaphoto/0.45 (its 0001/0002 patches drop a hardcoded ``-lgomp``
    and let clang's ``-fopenmp`` pick up the SDK's libomp).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class SpacedConan(ConanFile):
    name = "spaced"
    version = "1.2.0-201605"
    description = ("Alignment-free sequence comparison using spaced-word "
                   "frequencies (DNA and protein)")
    license = "GPL-3.0-or-later"
    homepage = "http://spaced.gobics.de/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("bioinformatics", "sequence", "alignment", "spaced-words", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must be tested with `in`, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "spaced is only supported on Linux/OHOS, not %s" % self.settings.os)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cpp_standard(self):
        """C++ dialect flag from the Conan profile, not from a shell variable."""
        cppstd = str(self.settings.get_safe("compiler.cppstd") or "17")
        if cppstd.startswith("gnu"):
            cppstd = cppstd[3:]
        return cppstd

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from Conan conf, never from a bare ${CXX}.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cxx = compilers.get("cpp") if compilers else None
        if not cxx:
            raise RuntimeError(
                "tools.build:compiler_executables.cpp is not set in the profile")

        # Same three translation units and the same -O3 upstream asks for; the
        # output goes to the build folder so the source tree stays pristine.
        out = os.path.join(self.build_folder, "spaced")
        self.run("{cxx} -O3 -std=c++{std} -fopenmp -static-openmp "
                 "src/spaced.cc src/variance.cpp src/patternset.cpp -o {out}".format(
                     cxx=cxx, std=self._cpp_standard(), out=out),
                 cwd=self.source_folder)

    def package(self):
        # Upstream's Makefile has no install target, so the only deliverable is
        # the linked binary plus the two documentation files.
        copy(self, "spaced", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Upstream README is the tool's only user documentation (options list).
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "spaced"))
        # Conan normalises modes while copying, so restore the exec bit.
        os.chmod(os.path.join(self.package_folder, "bin", "spaced"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
