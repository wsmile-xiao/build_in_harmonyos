import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    """Consumer view: compile and link against the installed lrslib, then
    drive both the C API and the installed command line tools."""

    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _abs(dirs, base):
        return [d if os.path.isabs(d) else os.path.join(base, d) for d in dirs]

    def _find_dep(self, name):
        """Look a dependency up by package name.

        gmp is a *transitive* dependency of this test_package, so resolve it by
        name over the whole dependency set instead of assuming it is a direct
        entry of self.dependencies.
        """
        for ref, dep in self.dependencies.items():
            ref_str = str(getattr(ref, "ref", ref))
            if ref_str.split("/")[0] == name:
                return dep
        return None

    def _dep_dirs(self, name):
        dep = self._find_dep(name)
        if dep is None:
            return [], []
        cpp = dep.cpp_info.aggregated_components()
        base = dep.package_folder or ""
        return self._abs(cpp.includedirs, base), self._abs(cpp.libdirs, base)

    def _pkg_dirs(self):
        pkg = self._find_dep("lrslib")
        cpp = pkg.cpp_info.aggregated_components()
        base = pkg.package_folder or ""
        return self._abs(cpp.includedirs, base), self._abs(cpp.libdirs, base)

    def _build_probe(self):
        pkg_inc, pkg_lib = self._pkg_dirs()
        gmp_inc, gmp_lib = self._dep_dirs("gmp")

        # -DMA -DGMP selects the GMP back end of liblrs.so (its symbols carry
        # the _gmp suffix); lrslib.h refuses to compile without an explicit
        # arithmetic choice, and the GMP back end is the one whose public
        # header chain pulls in <gmp.h>.
        cc = os.environ.get("CC") or "clang"
        cmd = [cc, "-O2", "-DMA", "-DGMP",
               os.path.join(self.source_folder, "test_lrslib.c"),
               "-o", os.path.join(self.build_folder, "test_lrslib")]
        cmd += ["-I" + d for d in pkg_inc + gmp_inc]
        cmd += ["-L" + d for d in pkg_lib + gmp_lib]
        cmd += ["-llrs"]
        cmd += ["-Wl,-rpath," + d for d in pkg_lib]
        self.output.info("compiling consumer probe: " + " ".join(cmd))
        self.run(" ".join(cmd))

    def build(self):
        self._build_probe()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link only")
            return

        pkg_folder = self._find_dep("lrslib").package_folder
        bindir = os.path.join(pkg_folder, "bin")
        probe = os.path.join(self.build_folder, "test_lrslib")
        cube = os.path.join(self.source_folder, "cube.ine")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = shutil.which("bash") or "/bin/sh"

        # 1. C API: the probe enumerates hypercubes of dimension 2..4 through
        #    the public headers and asserts the exact vertex counts 4/8/16.
        #    Run twice: under conanrun (the conventional consumer environment)
        #    and in a bare environment (the probe carries its own rpath).
        self.run(f"{bash} -c '{probe}'", env="conanrun")
        self.run(f"{bash} -c '{probe}'")

        # 2. Installed tools, deliberately WITHOUT conanrun.  This is the only
        #    run that proves the $ORIGIN/../lib RUNPATH is correct - under
        #    conanrun LD_LIBRARY_PATH is injected and would mask a broken
        #    RUNPATH.
        for tool, flag in (("lrs", "--version"), ("lrs", "--help"),
                           ("lrsnash", "--version"), ("redund", "--version"),
                           ("minrep", "--version"), ("fel", "--version")):
            self.run(f"{bash} -c '{bindir}/{tool} {flag} > /dev/null'")

        # 3. Real computation through the installed binary in the same bare
        #    environment: upstream's own cube.ine is the 3-cube, i.e. exactly
        #    8 vertices.
        self.run(f"{bash} -c '{bindir}/lrs {cube} | grep -q \"vertices=8\"'")

        # 4. The three argv[0] aliases must really *dispatch*: each one selects a
        #    different mode of the same binary, so assert the mode-specific
        #    output rather than just a successful load (--version returns before
        #    the argv[0] dispatch and therefore cannot prove it).
        for tool, marker in (("redund", "checking for redundant rows only"),
                             ("minrep", "minimum representation"),
                             ("fel", "no project/eliminate option found")):
            self.run(f"{bash} -c '{bindir}/{tool} {cube} | grep -q \"{marker}\"'")
