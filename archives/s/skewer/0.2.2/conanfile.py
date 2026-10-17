#!/usr/bin/env python3
"""Conan recipe — skewer 0.2.2 (single bare Makefile, C++ CLI application).

skewer implements a bit-masked k-difference matching algorithm for adapter
trimming of next-generation sequencing (NGS) reads.  Upstream is
https://github.com/relipmoc/skewer (transferred from SourceForge); the release
tag is the bare version ``0.2.2`` (no ``v`` prefix).

Build system: ONE hand-written Makefile — no configure script, no CMake, no
autotools.  Everything is driven by GNU make's ``.cpp.o`` suffix rule, and the
build is in-source (objects land next to the sources).

Two upstream defects block a build on any non-Linux-GCC host; both are handled
*without* editing the source tree (items 1. and 2. below).  A third defect is a
runtime portability bug that cannot be worked around from the recipe, so this
recipe carries exactly ONE source patch, registered under ``patches:`` in
``conandata.yml`` and applied by ``apply_conandata_patches()`` in build():

  1. ``CXX=g++`` is a plain assignment at Makefile:1.  The OHOS toolchain
     provides clang/clang++ only and there is no ``g++`` alias on PATH, so the
     very first compile step dies (reproduced on the HarmonyOS PC)::

         g++ -c -O2 src/main.cpp -o src/main.o
         make: g++: No such file or directory
         make: *** [Makefile:35: src/main.o] Error 127

     Because it is a *simple* assignment (not ``override``), a command-line
     variable beats it, which is exactly what GNU make's own manual prescribes
     for picking the compiler.  build() therefore runs
     ``make CXX=<resolved clang++> -j1`` — R33 compliant: the compiler path
     comes from the Conan conf (profile
     ``tools.build:compiler_executables``), never from ``$CXX``/``$CC``/
     ``$CFLAGS`` shell variables, which are empty on the release worker.

     Note ``CXXFLAGS?=-c`` at Makefile:3 is required because the
     compile recipe at Makefile:35 is ``$(CXX) $(CXXFLAGS) $< -o $@`` and
     does not spell out ``-c``.  Conan can export CXXFLAGS (the CI log shows
     ``-fPIC -O2``), which makes make skip the ``?=` default.  build()
     preserves inherited flags and prepends ``-c`` when it is absent.  The
     link recipe at Makefile:32 does not use CXXFLAGS, so this keeps ``-c``
     limited to compilation.

  2. The install target is ``install: mv -f $(EXECUTABLE) /usr/local/bin``
     (Makefile:47-48): a burned-in absolute destination, no PREFIX variable and
     no DESTDIR support, and it *moves* the binary out of the build tree.
     Reproduced on the HarmonyOS PC (where /usr/local does not exist at all)::

         mv -f skewer /usr/local/bin
         mv: bad 'skewer': No such file or directory
         make: *** [Makefile:48: install] Error 1

     (toybox ``mv`` names the *source* operand even though the missing
     destination directory is the real cause — a red herring worth recording.)
     ``make -n install DESTDIR=<dir>`` still prints the bare
     ``mv -f skewer /usr/local/bin``, proving DESTDIR/PREFIX are ignored.
     package() therefore never calls ``make install``; it copies the binary
     produced by build() into the package bin/ folder itself, so no host
     absolute path ever reaches the artifact.

  3. ``cFQ::tag`` (src/fastq.h:91) and the local ``c`` (src/fastq.cpp:93) are
     plain ``char`` variables that receive ``fgetc()``'s ``int`` return value and
     are then compared against ``EOF``.  On the OHOS target plain ``char`` is
     *unsigned* (``clang -dumpmachine`` = ``aarch64-unknown-linux-ohos``;
     ``limits.h`` yields ``CHAR_MIN == 0``; ``__CHAR_UNSIGNED__`` is predefined),
     so ``EOF`` (-1) is not representable there and all three sentinel tests are
     dead code -- clang says exactly that while compiling (measured on the
     HarmonyOS PC with the OHOS SDK clang 15.0.4)::

         src/fastq.cpp:87:9: warning: result of comparison of constant -1 with
             expression of type 'char' is always false
             [-Wtautological-constant-out-of-range-compare]
         src/fastq.cpp:96:24: warning: result of comparison of constant -1 with
             expression of type 'char' is always true
             [-Wtautological-constant-out-of-range-compare]
         src/fastq.cpp:104:9: warning: result of comparison of constant -1 with
             expression of type 'char' is always true
             [-Wtautological-constant-out-of-range-compare]

     Run-time consequence: once the input is exhausted ``readRecord()`` cannot
     return ``-1`` (EOF); it falls through and returns ``-2``, i.e. a bogus
     "Malformed fastq record N: no '@' for id" on stderr.  The worker loop in
     src/main.cpp treats ``rc < -1`` as a parse error and ``continue``s *without*
     processing the records already read into that block::

         if(rc < 0){ pTaskMan->finish();
                     if(rc < -1) continue;   // error
                     if(nItemCnt == 0) continue; }

     Its block size is ``nBasicSize * n_threads``, where ``nBasicSize`` is
     ``(len > 800 MB) ? 10 : (len / 100 MB + 2)`` (src/main.cpp:819-821) -- so it
     is 2 for every input under 100 MB, 3..9 up to 800 MB and 10 above.  On a
     small input with ``-t 1`` one block therefore holds exactly 2 records, so
     when the tail of a FASTQ with an ODD record count is read, the single record
     already sitting in that block is thrown away (bigger inputs or more threads
     lose 1..blockSize-1 tail records).  Measured with the packaged binary
     PC -- 5 records -> "4 reads processed", 7 -> 6, 9 -> 8, while the even
     counts 4/6/8/12 are unaffected because the last block fills up completely.

     Fix: patches/0001-fix-char-eof-sentinel.patch widens only those two
     declarations from ``char`` to ``int`` -- the value range ``fgetc()`` is
     specified to return.  No algorithm change, no platform macro, no behaviour
     change on signed-char hosts, so the patch stays upstreamable.  This is the
     prescription of the knowledge-base entry
     ``DRAFT-8543-plain-char-eof-sentinel-infinite-loop``; there the lost exit
     condition spins at 100% CPU, here the same lost sentinel turns EOF into a
     bogus parse error -- same root cause, different symptom.

Dependencies: none from the artifact registry.  The sources are 4 .cpp + 4 .h
pure C++/POSIX (stdio/unistd/getopt/search/time/pthread + libc++ containers);
the Makefile links ``-pthread`` (LDFLAGS) and ``-lrt`` (LDLIBS), both provided
by the OHOS musl libc / SDK sysroot.  There are no image or codec backends
(libpng / libjpeg / webp / sixel are not referenced anywhere), so the
"zero external library dependency" reading of the upstream is correct.

Upstream tests: none exist (audited — see test_package/MANIFEST.yml), so build()
does not run ``make check``; ``make -n check`` fails with
``No rule to make target 'check'``.  Evidence for the "no tests" declaration and
all consumer-side verification live in test_package/.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class SkewerConan(ConanFile):
    name = "skewer"
    version = "0.2.2"
    description = (
        "skewer — a fast and accurate adapter trimmer and quality filter for "
        "next-generation sequencing (NGS) single-end, paired-end and LMP reads."
    )
    license = "MIT"
    homepage = "https://github.com/relipmoc/skewer"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: never compare settings.os with ==
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is only prepared for Linux/OHOS targets, "
                f"not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cxx = self._resolve_cxx()
        inherited_cxxflags = os.environ.get("CXXFLAGS", "").strip()
        if "-c" not in shlex.split(inherited_cxxflags):
            inherited_cxxflags = "-c" + (
                f" {inherited_cxxflags}" if inherited_cxxflags else ""
            )
        # Keep the flags as an environment value so Makefile's += -O2 still applies.
        cxxflags_arg = shlex.quote(inherited_cxxflags)
        cxx_arg = shlex.quote(cxx)
        self.output.info(
            f"skewer build: make CXX={cxx} CXXFLAGS={inherited_cxxflags!r} -j1"
        )
        # R9: -j1; the upstream link rule explicitly lists every object.
        # The .cpp.o rule omits -c, so ensure Conan's inherited flags include it.
        self.run(
            f"CXXFLAGS={cxxflags_arg} make CXX={cxx_arg} -j1",
            cwd=self.source_folder,
        )

    def _resolve_cxx(self):
        """Return a C++ compiler path usable by ``make CXX=...`` (R33).

        Source of truth is the Conan conf (the OHOS profile pins
        tools.build:compiler_executables).  Some HMBS hosts carry a stale conf
        path, so fall back to PATH lookup and finally to the bare name
        (identical fallback chain to the merged abbtr/bwm recipes).  Plain
        isfile() probing only — no X_OK probing (R49: HMDFS ignores chmod and
        would make an X_OK test always fail).
        """
        try:
            conf_cxx = (
                self.conf.get("tools.build:compiler_executables:cpp",
                              check_type=str) or ""
            ).split()[0]
        except Exception:
            conf_cxx = ""
        if conf_cxx and os.path.isfile(conf_cxx):
            return conf_cxx
        for name in ("clang++", "g++"):
            found = shutil.which(name)
            if found and os.path.isfile(found):
                self.output.info(
                    f"skewer: conf CXX {conf_cxx!r} unusable, using {found}")
                return found
        return "clang++"

    def package(self):
        # Upstream `make install` is unusable on OHOS (see module docstring),
        # so package() stages the binary itself.
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "skewer", src=self.source_folder, dst=bin_dir)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"))
        exe = os.path.join(bin_dir, "skewer")
        if os.path.isfile(exe):
            try:
                os.chmod(exe, 0o755)
            except OSError:
                # HMDFS may ignore chmod (E046); never fail packaging on it.
                self.output.warning(f"skewer: chmod 0755 failed for {exe}")
        else:
            raise Exception(f"skewer binary missing after build: {exe}")

    def package_info(self):
        # application package: exports no cpp_info.libs at all
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
