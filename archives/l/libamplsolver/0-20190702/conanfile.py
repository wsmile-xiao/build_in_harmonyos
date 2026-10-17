#!/usr/bin/env python3
"""Conan recipe — libamplsolver 0-20190702 (AMPL Solver Library).

NOTE on versioning: the Conan package version is "0-20190702" (hyphen),
matching the archive directory and the feat/libamplsolver-0-20190702 branch
so L0n/L0m branch&dir gates match. This corresponds to the netlib
ampl/solvers 2019-07-02 snapshot, packaged upstream by Debian under the
*filename* "libamplsolver_0~20190702.orig.tar.xz" (the '~' only lives in
the Debian pool archive filename, never in the Conan reference — Conan 2
rejects '~' in a package version, E563).

Routines that help solvers work with AMPL: reading AMPL's generic output
(.nl) files and writing solution (.sol) files. Pure C, legacy raw-Makefile
build (makefile.u), no configure/CMake, no third-party dependencies.

Build notes:
  - Upstream ships only makefile.{u,vc,lc,sy,wat} — there is NO plain
    `makefile`/`Makefile`, so `make` alone would fail. We must invoke
    `make -f makefile.u` (R33: never bare `${CC}`/`CFLAGS`; resolve the
    compiler from Conan conf).
  - The Makefile generates `arith.h` at build time by compiling+running a
    tiny probe (`arithchk.c`), which requires running the produced binary
    on the target — fine on the HarmonyOS aarch64 device.
  - `make` must run in the source folder (raw make writes objects next to
    sources), hence `cwd=self.source_folder`.
  - The build produces `amplsolver.a` (no `lib` prefix). We rename it to
    `libamplsolver.a` in package() so consumers can link with the standard
    `-lamplsolver` (via cpp_info.libs = ["amplsolver"]).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibamplsolverConan(ConanFile):
    name = "libamplsolver"
    version = "0-20190702"
    description = "AMPL Solver Library - routines for reading AMPL .nl files and writing .sol files"
    license = "BSD-3-Clause"
    homepage = "https://ampl.com/netlib/ampl/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Conan 2 requires a `library` package_type to declare a `shared` option
    # (ERROR: 'Package type is "library", but no "shared" option declared').
    # The upstream legacy makefile.u only builds a static `amplsolver.a`, so we
    # declare the option to satisfy the graph but only support static; shared
    # is rejected in validate() rather than silently ignored.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libamplsolver 0-20190702 upstream makefile.u only builds a "
                "static library (amplsolver.a); shared=True is not supported"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _audit_upstream_tests(self):
        """Audit the upstream tree for automated tests (machine evidence).

        The libamplsolver 0-20190702 upstream source ships no automated
        test suite: makefile.u defines only all/arith.h/stdi01.h/
        details.c/systemprintf/xsum.out/clean targets — there is no
        `check`/`test` target and no tests/ directory. Run the audit grep
        against the real source tree so the conan create log carries the
        machine evidence; the no_tests marker itself is emitted by the
        test_package stage (MANIFEST upstream_test_in_build: false, same
        pattern as the gate-passing osmctools/sipcalc/xidle/aribb24
        recipes).
        """
        mk = os.path.join(self.source_folder, "makefile.u")
        audit_cmd = (
            "grep -nE '^[a-zA-Z0-9_.-]+:' \"%s\" | grep -iE 'check|test'; "
            "echo '-- no check/test targets above => no upstream tests --'"
            % mk
        )
        self.run(audit_cmd)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler must come from Conan conf, never bare shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # The makefile.u rules hard-code `ar`/`ranlib`/`sed`/`uname` from
        # PATH; only the `.c.o` implicit rule honours $(CC). Use -fPIC so
        # the static lib can be linked into shared consumers.
        # R9: always -j1 for this legacy single-threaded makefile.
        self.run(f"make -f makefile.u CC=\"{cc}\" CFLAGS='-O2 -fPIC' -j1",
                 cwd=self.source_folder)

        # Machine evidence that upstream ships no automated tests.
        self._audit_upstream_tests()

    def package(self):
        # Headers generated at build time (arith.h, stdio1.h) as well as
        # shipped ones (asl.h, asl_pfg.h, asl_pfgh.h, ...).
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # Copy amplsolver.a then rename to libamplsolver.a so consumers
        # can link with the standard `-lamplsolver` (cpp_info.libs below).
        # Same proven pattern as archives/b/bcrypt and archives/a/argus.
        lib_dir = os.path.join(self.package_folder, "lib")
        copy(self, "amplsolver.a", self.source_folder, lib_dir)
        os.rename(os.path.join(lib_dir, "amplsolver.a"),
                  os.path.join(lib_dir, "libamplsolver.a"))

    def package_info(self):
        self.cpp_info.libs = ["amplsolver"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "AMPLSolver")
        self.cpp_info.set_property("cmake_target_name", "AMPLSolver::AMPLSolver")
