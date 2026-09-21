#!/usr/bin/env python3
"""Conan recipe for lrslib 0.73 (upstream release 7.3).

lrslib is David Avis' reverse-search implementation for vertex/facet
enumeration of convex polyhedra in exact rational arithmetic.  Upstream ships
a hand written ``makefile`` (no ``configure``, no CMake, no install
autotools) that produces

  * ``liblrs.so`` - the C library.  It carries three arithmetic back ends at
    once (64 bit, 128 bit and GMP); the caller selects one by compiling with
    the matching macros (``-DMA -DGMP``, ``-DMA -DB128 -DLRSLONG`` or
    ``-DMA -DLRSLONG``) which rename every symbol via ``suf()``.
  * the command line tools ``lrs`` and ``lrsnash``.  ``redund``, ``minrep``
    and ``fel`` are the very same binary dispatched on ``argv[0]``.

The recipe builds upstream's own ``all-shared`` target - the same target the
upstream ``install`` rule consumes - installs library, public headers and
tools, then runs the complete upstream regression battery (``ine/test/*.ine``)
through the freshly built ``lrs``.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# One ``lrs`` invocation per upstream regression input.  ``mit.ine`` needs
# ~210 s on the reference device, everything else finishes in <= 2 s.
_UPSTREAM_CASE_TIMEOUT = 900

# Upstream regression inputs that legitimately produce no ``*Totals:`` line:
# cp4/ep are conversion modes, inf has no feasible solution and left/right are
# one-sided H<->V probes.  Verified case by case on the device.
_UPSTREAM_NO_TOTALS = {"cp4.ine", "ep.ine", "inf.ine", "left.ine", "right.ine"}

# Inputs whose ``ext/test/`` companion really is the output of that very input,
# used as an independent oracle.  ``Mit.ext`` and ``mp5.ext`` come from other
# problem files, so they are deliberately not listed here.
_UPSTREAM_REFERENCE = {
    "cube.ine": ("cube.ext", 8),
    "tsp5.ine": ("tsp5.ext", 12),
}


class LrslibConan(ConanFile):
    name = "lrslib"
    version = "0.73"
    description = ("Reverse search vertex/facet enumeration for convex polyhedra in "
                   "exact rational arithmetic (lrslib C library plus the lrs, "
                   "redund, minrep, fel and lrsnash command line tools)")
    license = "GPL-2.0-or-later"
    homepage = "https://cgm.cs.mcgill.ca/~avis/C/lrs.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def configure(self):
        # Upstream's makefile has a shared-library target (all-shared, the one
        # its own install rule consumes) and no static-library target at all,
        # so refuse the impossible configuration instead of building a lie.
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "lrslib/0.73 is shared-only: the upstream makefile provides no "
                "static library target")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lrslib.h -> ARITH ("lrsgmp.h") -> <gmp.h>: gmp.h is part of the
        # *public* header chain of the GMP back end, so consumers of lrslib
        # need gmp's include dir as well.  Without transitive_headers the
        # package builds and its own tests pass, and only downstream
        # consumers fail to compile.
        self.requires("gmp/6.3.0", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _dep_dirs(self, name):
        """Absolute include/lib dirs of a dependency.

        ``cpp_info`` entries are relative unless the package folder is known,
        so resolve against ``package_folder`` as a guard (a skipped
        transitive dependency would otherwise yield a bare ``lib``).
        """
        dep = self.dependencies[name]
        cpp = dep.cpp_info.aggregated_components()
        base = dep.package_folder or ""
        inc = [d if os.path.isabs(d) else os.path.join(base, d) for d in cpp.includedirs]
        lib = [d if os.path.isabs(d) else os.path.join(base, d) for d in cpp.libdirs]
        return inc, lib

    def _compiler(self):
        """C compiler for the upstream makefile.

        The profile declares ``tools.build:compiler_executables`` as a dict;
        reading the ``:c`` sub-key form raises ConanException ("does not exist
        in configuration list") because only the aggregate key is declared.
        """
        conf = self.conf.get("tools.build:compiler_executables", default=None)
        if isinstance(conf, dict):
            return conf.get("c") or conf.get("cpp") or "clang"
        return "clang"

    def _cflags(self):
        """CFLAGS handed to the upstream makefile.

        * ``-I lrsarith-011/`` is upstream's own ${ARITH} include dir.
        * gmp include/lib dirs: several upstream link rules call ``-lgmp``
          without ``-L${LIBDIR}``, so the lib dir has to travel in CFLAGS.
        """
        gmp_inc, gmp_lib = self._dep_dirs("gmp")
        flags = ["-O3", "-Wall", "-I%s" % os.path.join(self.source_folder, "lrsarith-011")]
        flags += ["-I%s" % d for d in gmp_inc]
        flags += ["-L%s" % d for d in gmp_lib]
        return " ".join(flags)

    def _jobs(self):
        # conan defaults tools.build:jobs to os.cpu_count(), which is 20 on
        # this device while the box is shared.  The upstream makefile has no
        # job control of its own, so cap it here.
        return self.conf.get("tools.build:jobs", default=2, check_type=int) or 2

    # ------------------------------------------------------------------ #
    # build
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)

        gmp_inc, gmp_lib = self._dep_dirs("gmp")
        self.run(
            'make -j{jobs} CC="{cc}" CFLAGS="{cflags}" INCLUDEDIR="{inc}" '
            'LIBDIR="{lib}" SHLIBFLAGS="-L{lib}" all-shared'.format(
                jobs=self._jobs(),
                cc=self._compiler(),
                cflags=self._cflags(),
                inc=gmp_inc[0],
                lib=gmp_lib[0],
            ),
            cwd=self.source_folder,
        )

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run every upstream regression input through the freshly built lrs.

        ``ine/test/`` is upstream's regression battery: one complete
        enumeration problem per file.  Each file is one upstream test case and
        must terminate with status 0 and report its own ``*Totals:`` line
        (``_UPSTREAM_NO_TOTALS`` lists the conversion / infeasible modes that
        legitimately have none).  ``cube.ine`` and ``tsp5.ine`` additionally
        carry an upstream reference output under ``ext/test/`` whose declared
        row count must match the number of vertices lrs reports.
        """
        runner = "./lrs-shared"
        tmpdir = os.path.join(self.build_folder, "upstream-test-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        outdir = os.path.join(self.build_folder, "upstream-test-out")
        os.makedirs(outdir, exist_ok=True)

        timeout = shutil.which("timeout")
        cases = sorted(glob.glob(os.path.join(self.source_folder, "ine", "test", "*.ine")))
        if len(cases) != 30:
            raise ConanException(
                "upstream regression battery changed: expected 30 inputs in "
                "ine/test/, found %d" % len(cases))

        # LD_LIBRARY_PATH: the build tree keeps liblrs.so next to the binary,
        # the installed tree keeps it in ../lib (RUNPATH).  TMPDIR: lrs writes
        # its overflow-restart file through mkstemp().  Inline variable
        # assignments (rather than `env VAR=...`) keep the command independent
        # of where the platform keeps its `env` binary.
        env = ("LD_LIBRARY_PATH={src}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}} "
               "TMPDIR={tmp}").format(src=self.source_folder, tmp=tmpdir)

        failures = []
        ran = 0
        for case in cases:
            name = os.path.basename(case)
            log = os.path.join(outdir, name + ".log")
            guard = ("%s %s " % (timeout, _UPSTREAM_CASE_TIMEOUT)) if timeout else ""
            self.run(
                '{env} {guard}{runner} "{case}" > "{log}" 2>&1'.format(
                    env=env, guard=guard, runner=runner, case=case, log=log),
                cwd=self.source_folder,
            )
            text = open(log, encoding="utf-8", errors="replace").read()
            ran += 1
            if self._totals_vertices(text) is None and name not in _UPSTREAM_NO_TOTALS:
                failures.append("%s: no *Totals: line" % name)
                continue
            want = self._reference_vertices(name)
            if want is not None:
                got = self._totals_vertices(text)
                if got != want:
                    failures.append("%s: upstream reference expects %d vertices, lrs reported %s"
                                    % (name, want, got))

        self.output.info("upstream regression battery: %d/%d cases executed, %d failed"
                         % (ran - len(failures), ran, len(failures)))
        if failures:
            raise ConanException("upstream regression failures: " + "; ".join(failures))

    @staticmethod
    def _totals_vertices(text):
        """Vertices reported by lrs' own final ``*Totals:`` line.

        ``*Elapsed time:`` is printed by the driver even when enumeration
        aborted early, so the presence of the totals line - not the trailer -
        is what separates a completed run from a silent no-op.
        """
        for line in text.splitlines():
            if "*Totals:" in line and "vertices=" in line:
                token = line.split("vertices=", 1)[1].split()[0]
                return int(token)
        return None

    def _reference_vertices(self, case_name):
        """Row count declared by the matching upstream reference output.

        Only ``cube.ine`` and ``tsp5.ine`` have an ``ext/test/`` companion that
        really is the output of that very input; ``Mit.ext``/``mp5.ext`` are
        produced from different (older) problem files and must not be used as
        an oracle - note that the platform filesystem is case-insensitive, so
        a blind ``mit`` -> ``Mit.ext`` lookup would silently compare against
        the wrong file.
        """
        entry = _UPSTREAM_REFERENCE.get(case_name)
        if entry is None:
            return None
        ref_name, _expected = entry
        refdir = os.path.join(self.source_folder, "ext", "test")
        # Exact-case match against the real directory listing.
        if ref_name not in os.listdir(refdir):
            raise ConanException("upstream reference %s missing from ext/test/" % ref_name)
        with open(os.path.join(refdir, ref_name), encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
        for index, line in enumerate(lines):
            if line.strip() == "begin" and index + 1 < len(lines):
                for field in lines[index + 1].split():
                    if field.isdigit():
                        return int(field)
                return None
        return None

    # ------------------------------------------------------------------ #
    # package
    # ------------------------------------------------------------------ #
    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

        for header in ("lrslib.h", "lrsdriver.h", "lrsrestart.h",
                       os.path.join("lrsarith-011", "lrsgmp.h"),
                       os.path.join("lrsarith-011", "lrslong.h"),
                       os.path.join("lrsarith-011", "lrsmp.h")):
            copy(self, header, self.source_folder,
                 os.path.join(self.package_folder, "include", "lrslib"), keep_path=False)

        # Upstream's install target uses `install -t`, which does not exist on
        # this platform, so the layout is reproduced here explicitly.
        libdir = os.path.join(self.package_folder, "lib")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)

        sofile = "liblrs.so.1.0.0"
        copy(self, sofile, self.source_folder, libdir)
        for link in ("liblrs.so.1", "liblrs.so"):
            target = os.path.join(libdir, link)
            if os.path.lexists(target):
                os.remove(target)
            os.symlink(sofile, target)

        for built, installed in (("lrs-shared", "lrs"), ("lrsnash-shared", "lrsnash")):
            copy(self, built, self.source_folder, bindir, keep_path=False)
            renamed = os.path.join(bindir, built)
            final = os.path.join(bindir, installed)
            if renamed != final:
                if os.path.lexists(final):
                    os.remove(final)
                os.rename(renamed, final)
            os.chmod(final, 0o755)

        # lrs dispatches on argv[0]: these three names are the documented
        # aliases of the same binary (see redund(1)).
        for alias in ("redund", "minrep", "fel"):
            link = os.path.join(bindir, alias)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink("lrs", link)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lrslib")
        self.cpp_info.set_property("cmake_target_name", "lrslib::lrslib")
        self.cpp_info.set_property("pkg_config_name", "lrslib")
        self.cpp_info.libs = ["lrs"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
