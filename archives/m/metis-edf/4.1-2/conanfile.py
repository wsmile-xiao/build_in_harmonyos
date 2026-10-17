#!/usr/bin/env python3
"""Conan recipe for metis-edf 4.1-2 (Code_Aster / EDF fork of METIS 4.0.1).

metis-edf is the variant of METIS 4.0.1 that EDF ships for Code_Aster: all
``int`` counters were widened to ``long`` and an ``onmetis`` driver plus a
Code_Aster-specific file format (``fort.81`` in, ``fort.85`` out) were added.
The tarball layout is the classic 1998 one:

* ``Lib/``      -- the library ``libmetis.a`` (52 plain C files);
* ``Programs/`` -- the three programs upstream builds: ``onmetis`` (the
  Code_Aster driver), ``pmetis`` and ``kmetis`` (plain METIS partitioning);
* ``Test/``     -- the upstream test: run ``onmetis`` on a ``fort.81`` produced
  by Code_Aster, plus an ``--version`` check.

Build system: hand-written Makefiles that call ``CONFIG/configure`` (which
runs ``uname`` and emits ``Makefile.in``).  Two things make it unusable as-is
on OHOS:

1. ``CONFIG/configure`` only accepts SunOS/OSF1/IRIX64/Linux/Cygwin and hard
   codes gcc/g77/gfortran.  Rather than patching that shell script we compile
   the sources directly with the OHOS clang (same approach as the other
   recipes in this repo).
2. ``onmetis`` links three small **Fortran** helpers (``lect00.f``/``lect11.f``/
   ``ecri11.f``) that read/write ``fort.81``/``fort.85``.  There is no Fortran
   compiler in the OHOS toolchain (and conan has no gfortran package), so this
   recipe ships ``port_fortran_io.c``: a direct ISO-C port of those three
   routines (the ``.f`` files are left untouched in the tree).  The rest of
   metis-edf -- including the whole ordering/partitioning library -- is C.

``build()`` compiles the library and the three programs and then runs the two
upstream ``Test/`` checks for real; ``test_package`` exercises the installed
library through the public METIS API and the installed CLIs.
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

UPSTREAM_TESTS = 2


class MetisEdfConan(ConanFile):
    name = "metis-edf"
    version = "4.1-2"
    description = ("METIS 4.0.1 adapted by EDF for Code_Aster: serial graph "
                   "partitioning, mesh partitioning and fill-reducing "
                   "orderings, plus the onmetis/pmetis/kmetis programs")
    license = "METIS"
    homepage = "http://glaros.dtc.umn.edu/gkhome/metis/metis/overview"
    url = ""

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "metis-edf OHOS adaptation is validated on Linux/OHOS only, "
                "not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "port_fortran_io.c", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # metis-edf has no external dependencies (only libc + libm).
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        copy(self, "port_fortran_io.c", self.export_sources_folder,
             os.path.join(self.source_folder, "Programs"))

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _archiver(self):
        cc = self._compiler("c", "clang")
        directory = os.path.dirname(cc)
        if directory:
            for candidate in ("llvm-ar", "ar"):
                path = os.path.join(directory, candidate)
                if os.path.isfile(path):
                    return path
        return shutil.which("llvm-ar") or shutil.which("ar") or "ar"

    @staticmethod
    def _cmd(argv):
        return " ".join(shlex.quote(str(a)) for a in argv)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        lib_dir = os.path.join(src, "Lib")
        prog_dir = os.path.join(src, "Programs")
        obj_dir = os.path.join(src, "obj")
        os.makedirs(obj_dir, exist_ok=True)

        cc = self._compiler("c", "clang")
        ar = self._archiver()
        common = [cc, "-O2", "-fcommon", "-std=gnu17",
                  "-Wno-implicit-function-declaration", "-Wno-implicit-int",
                  "-Wno-format", "-Wno-shift-op-parentheses",
                  "-I", lib_dir]

        # 1) libmetis.a from all of Lib/*.c (METIS changed int -> long here).
        lib_objs = []
        for source in sorted(glob.glob(os.path.join(lib_dir, "*.c"))):
            obj = os.path.join(obj_dir, os.path.basename(source)[:-2] + ".o")
            self.run(self._cmd(common + ["-c", source, "-o", obj]), cwd=src)
            lib_objs.append(obj)
        libmetis = os.path.join(src, "libmetis.a")
        self.run(self._cmd([ar, "rcs", libmetis] + lib_objs), cwd=src)
        if not os.path.isfile(libmetis):
            raise ConanInvalidConfiguration("libmetis.a was not produced")

        # 2) the three programs upstream builds (pmetis/kmetis use the plain
        #    io.c reader; onmetis uses the Code_Aster io_aster.c + the Fortran
        #    I/O helpers now provided by port_fortran_io.c).
        programs = {
            "pmetis": ["pmetis.c", "io.c"],
            "kmetis": ["kmetis.c", "io.c"],
            "onmetis": ["onmetis.c", "io_aster.c", "smbfactor.c",
                        "port_fortran_io.c"],
        }
        for binary, sources in programs.items():
            args = common + [os.path.join(prog_dir, s) for s in sources]
            args += [libmetis, "-o", os.path.join(src, binary), "-lm"]
            self.run(self._cmd(args), cwd=src)
            if not os.path.isfile(os.path.join(src, binary)):
                raise ConanInvalidConfiguration(
                    "build did not produce the '%s' program" % binary)

        self._run_upstream_tests(src)

    def _run_upstream_tests(self, src):
        """Reproduce the two Test/Makefile targets (fort.85 and vers_check)."""
        run_dir = os.path.join(src, "upstream-test")
        os.makedirs(run_dir, exist_ok=True)
        copy(self, "fort.81", os.path.join(src, "Test"), run_dir)
        onmetis = os.path.join(src, "onmetis")

        # Test 2 (target vers_check): `onmetis --version`.
        self.run(self._cmd([onmetis, "--version"]) + " > version.txt 2>&1",
                 cwd=run_dir, ignore_errors=True)
        with open(os.path.join(run_dir, "version.txt"), encoding="utf-8",
                  errors="replace") as handle:
            version = handle.read().strip().splitlines()
        if not version or version[0].strip() != "metis-edf-4.1":
            raise ConanInvalidConfiguration(
                "upstream Test 2 (--version) failed: got %r" % version)

        # Test 1 (target fort.85): run onmetis on the Code_Aster fort.81.
        self.run(self._cmd([onmetis, "fort.81"]), cwd=run_dir)
        iperm_path = os.path.join(run_dir, "fort.81.iperm")
        fort85_path = os.path.join(run_dir, "fort.85")
        for path in (iperm_path, fort85_path):
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    "upstream Test 1 did not produce %s" % path)

        iperm = self._read_ints(iperm_path)
        n = len(iperm)
        if sorted(iperm) != list(range(n)):
            raise ConanInvalidConfiguration(
                "fort.81.iperm is not a permutation of 0..n-1")

        with open(fort85_path, encoding="ascii", errors="replace") as handle:
            lines = handle.read().splitlines()
        header = lines[0]
        nbsn = int(header[0:10])
        maxlnz = int(header[30:40])
        lgind = int(header[40:50])
        values = [int(tok) for tok in " ".join(lines[1:]).split()]
        if len(values) != 2 * n + 2 * nbsn + 1:
            raise ConanInvalidConfiguration(
                "fort.85 has %d integers, expected %d"
                % (len(values), 2 * n + 2 * nbsn + 1))
        invp = values[0:n]
        if invp != [v + 1 for v in iperm]:
            raise ConanInvalidConfiguration(
                "fort.85 invp column does not match fort.81.iperm + 1")
        if nbsn <= 0 or maxlnz <= 0 or lgind <= 0:
            raise ConanInvalidConfiguration("fort.85 has empty supernode data")
        self.output.info(
            "upstream Test 1: onmetis produced a valid ordering "
            "(n=%d, supernodes=%d, maxlnz=%d, lgind=%d)" % (n, nbsn, maxlnz, lgind))
        self.output.info("upstream tests executed: %d/%d" % (UPSTREAM_TESTS, UPSTREAM_TESTS))

    @staticmethod
    def _read_ints(path):
        with open(path, encoding="ascii", errors="replace") as handle:
            return [int(tok) for tok in handle.read().split()]

    def package(self):
        copy(self, "libmetis.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        headers = ("metis.h", "defs.h", "struct.h", "macros.h", "rename.h",
                   "proto.h")
        for header in headers:
            copy(self, header, os.path.join(self.source_folder, "Lib"),
                 os.path.join(self.package_folder, "include"))
        for binary in ("onmetis", "pmetis", "kmetis"):
            copy(self, binary, self.source_folder,
                 os.path.join(self.package_folder, "bin"))
        copy(self, "INSTALL", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "metis-edf")
        self.cpp_info.libs = ["metis"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
