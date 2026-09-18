#!/usr/bin/env python3
"""Conan recipe for lout 3.43.4 (Basser Lout document formatting system).

lout builds two executables (lout, prg2lout) via a single non-recursive
GNU makefile, plus a runtime data tree (include/ data/ hyph/ font/ maps/
locale/) that the executables locate at run time via $LOUTLIB, the
argv[0]-relative path, or the compiled-in LIB_DIR fallback.

Upstream has NO shared-library variant: the only link rule in the
makefile is ``lout: $(OBJS)`` (plain executable) and ``make install``
installs binaries + data files only.  Therefore this recipe defines no
``shared`` option (evidence recorded in notes.md).

OHOS adaptation (full root-cause analysis in notes.md):
  * patch 0001: catopen() returns (nl_catd)-1 on failure.  lout's
    condcatgets() macro only checked for NULL, so the -1 sentinel was
    passed to catgets(), which OHOS musl dereferences without checking
    -> SIGSEGV in every document-formatting run.  glibc tolerates the
    invalid descriptor and returns the fallback string, which is why
    upstream never noticed.  Same guard style as the catclose() fix
    upstream shipped in 3.43.
  * The OHOS cross toolchain travels via the ``CC`` make variable (the
    makefile re-appends its own CFLAGS, so CC is the only injection
    point).
  * USELOC stays 1: locale catalogs are a genuine upstream feature and
    the patched sentinel path is now handled correctly.

Upstream testing: ``make test`` (doc/user) requires the *previous*
release binary (lout-3.40) as reference; that binary does not exist for
OHOS, so the runnable upstream-test core is executed instead — the exact
invocation ``make test`` performs with the *new* binary: ``lout -r3 all``
(3-pass PS formatting of the full 400-page user manual), plus a single
plain-text pass ``-p -r1 all`` (the plain backend truncates to front
matter under multi-run — upstream behavior, see notes.md), from a clean
database state.  Executed in build() (L2) and re-verified in
test_package as a consumer.
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class LoutConan(ConanFile):
    name = "lout"
    version = "3.43.4"
    description = "Basser Lout - a document formatting system by Jeffrey H. Kingston"
    license = "GPL-2.0-only"
    homepage = "https://savannah.nongnu.org/projects/lout/"
    url = "https://savannah.nongnu.org/projects/lout/"

    # Executable-only package: upstream makefile has no .so target.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # NOTE: no `shared` option — see module docstring & notes.md.

    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # zero external runtime deps (zlib optional; PDF_COMPRESSION=0 default)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"][0]
        get(self, **src, strip_root=True)

    def configure(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "lout conanfile targets OHOS; os={} not supported".format(self.settings.os)
            )

    def generate(self):
        # Nothing to generate: no CMake/meson — plain makefile build driven
        # from build() with explicit CC.
        pass

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from Conan conf, never bare shell env.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"
        njobs = os.cpu_count() or 2

        # lout's makefile: `lout: $(OBJS)` then link; CCFLAGS/CFLAGS are
        # makefile-owned.  The only injection point for the OHOS toolchain
        # is CC (compiler path + target flags travel with the wrapper).
        self.run(
            f'make lout prg2lout -j{njobs} CC="{cc}"',
            env="conanbuild",
            cwd=self.source_folder,
        )

        # ── Upstream test core (L2): the exact work `make test` does with
        #    the new binary — format the full user manual, 3 passes
        #    (-r3 == index/cross-ref resolution), from clean database state.
        #    `make test` proper additionally diffs against a lout-3.40
        #    reference binary which does not exist for OHOS (see notes.md).
        import shutil
        import subprocess

        test_dir = os.path.join(self.build_folder, "upstream-test")
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        os.makedirs(test_dir)
        # doc/user "all" @Includes its module files (mybook etc.) from the
        # current directory, so the inputs must sit next to the output.
        # The doc files carry no extension (all, mybook, bas, ...); skip
        # known build artifacts and logs only.
        skip = {"README", "Makefile", "run.log"}
        for f in os.listdir(os.path.join(self.source_folder, "doc", "user")):
            if f in skip or f.startswith("user."):
                continue
            shutil.copy2(
                os.path.join(self.source_folder, "doc", "user", f),
                os.path.join(test_dir, f),
            )
        lib_dir = self._runtime_lib_dir()
        # lout resolves its runtime tree (include/data/hyph/maps/font) from
        # $LOUTLIB first, then argv[0]-relative ../../lib, then the
        # compiled-in LIB_DIR.  -I/-H/-D merely PREPEND to the search paths
        # and do not cover character maps (maps/) or fonts (font/), so the
        # clean way to point lout at a tree is LOUTLIB.
        env = dict(os.environ, LOUTLIB=lib_dir)
        # The plain-text backend truncates to front matter under multi-run
        # (-p -r2+) — an upstream 3.43.4 property, proven by an unpatched
        # USELOC=0 binary producing byte-identical 4,084 B output (see
        # notes.md); run 1 is complete, so plain text is verified single-pass.
        for doc, extra in (("user.ps", " -r3"), ("user.txt", " -p -r1")):
            # upstream `make test` removes the cross-ref database files
            # (*.ld *.ldx *.li) before each run — keep that clean state.
            # NB: no -s here: -s is CH_FLAG_SUPPRESS (AllowCrossDb=FALSE)
            # and upstream `make test` does NOT use it — suppressing the
            # cross database would disable exactly what -r3 exercises.
            for db in os.listdir(test_dir):
                if db.endswith((".ld", ".ldx", ".li")):
                    os.unlink(os.path.join(test_dir, db))
            out = os.path.join(test_dir, doc)
            cmd = f'"{self.source_folder}/lout"{extra} all -o "{out}"'
            self.output.info(f"L2 upstream test (LOUTLIB={lib_dir}): {cmd}")
            # lout returns 0 on success (warnings do not affect exit code;
            # verified against the full user manual run).
            rc = subprocess.call(cmd, shell=True, cwd=test_dir, env=env)
            if rc != 0:
                raise ConanException(
                    f"upstream test core failed: lout exited {rc} formatting {doc}"
                )
            if not os.path.exists(out) or os.path.getsize(out) == 0:
                raise ConanException(
                    f"upstream test core failed: {doc} missing or empty"
                )

    def _runtime_lib_dir(self):
        """Runtime data tree: prefer source tree (build-time tests), fall
        back to the installed package tree (res/lib, test_package)."""
        for base in (self.source_folder,
                     os.path.join(self.package_folder or "", "res", "lib")):
            if base and os.path.isdir(os.path.join(base, "data")):
                return base
        raise ConanException("lout runtime data tree not found")

    def package(self):
        # Executables -> bin/; runtime data tree -> res/lib (LOUTLIB).
        copy(self, "lout", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "prg2lout", self.source_folder, os.path.join(self.package_folder, "bin"))
        for d in ("include", "data", "hyph", "font", "maps"):
            copy(self, "*", os.path.join(self.source_folder, d),
                 os.path.join(self.package_folder, "res", "lib", d))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["res"]

    def test(self):
        # NB: not gated on can_run() — the OHOS conan fork forces
        # settings_build to Linux/x86_64 for standalone test runs, which
        # makes can_run() False and would skip the smoke entirely; the
        # CI machine runs OHOS aarch64 binaries natively (musl).
        self.run(f'"{self.package_folder}/bin/lout" --version', env="conanbuild")
