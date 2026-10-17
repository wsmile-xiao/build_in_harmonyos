#!/usr/bin/env python3
"""Conan L1 test_package for liblqr 0.4.3 (consumer view).

Compiles test_lqr_package.c against the packaged <lqr.h> + liblqr-1 via the
pkg-config files shipped inside the packages (lqr-1.pc Requires: glib-2.0),
and runs it, so the test really consumes the package products exactly the
way a downstream autotools/meson consumer would.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LiblqrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # basic_layout keeps the build folder out of the recipe source tree
        # (covered by the repository .gitignore).
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        # R33: compiler from Conan conf, not a shell variable.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = ce.get("c") or "clang"

        src = os.path.join(self.recipe_folder, "test_lqr_package.c")
        out = os.path.join(self.build_folder, "test_lqr_package")

        # Compile through pkg-config, exactly like a downstream consumer:
        #   $(pkg-config --cflags --libs lqr-1)
        # PkgConfigDeps writes lqr-1.pc / glib-2.0.pc into the generators
        # folder but does NOT export PKG_CONFIG_PATH itself (only
        # AutotoolsToolchain does that for the *library* build), so point
        # pkg-config at the generators folder explicitly.
        env = "export PKG_CONFIG_PATH={}".format(self.generators_folder)
        self.run(
            '{env} && "{cc}" {src} -o "{out}" $(pkg-config --cflags --libs lqr-1)'.format(
                env=env, cc=cc, src=src, out=out),
            env="conanbuild")

    def test(self):
        exe = os.path.join(self.build_folder, "test_lqr_package")

        # Explicit self.run() per repo requirement (L0d gate).
        self.run('"{}"'.format(exe), env="conanrun")
        self.output.success("liblqr test_package: C API carve checks passed")

        # ── OHOS-specific checks (shared package only) ────────────────
        # ELF64 / AArch64 / dynamic deps / RPATH policy of the packaged
        # library, exercised with the real readelf from the toolchain.
        pkg = self.dependencies["liblqr"].package_folder
        libdir = os.path.join(pkg, "lib")
        so = None
        for cand in ("liblqr-1.so.0.3.2", "liblqr-1.so.0", "liblqr-1.so"):
            p = os.path.join(libdir, cand)
            if os.path.exists(p) and not os.path.islink(p):
                so = p
                break
        if so is None:
            # static package: no .so to inspect; the direct-link + run
            # checks above already prove the static archive works.
            self.output.info("static package: skipping ELF shared-lib checks")
            return

        readelf = shutil.which("readelf") or "/usr/local/bin/readelf"
        out = subprocess.run([readelf, "-h", so], capture_output=True, text=True, check=True).stdout
        assert "Class:                             ELF64" in out, "liblqr-1.so is not ELF64"
        assert "Machine:                           AArch64" in out, "liblqr-1.so is not AArch64"
        self.output.info("[ok] liblqr-1.so is ELF64 AArch64")

        dyn = subprocess.run([readelf, "-d", so], capture_output=True, text=True, check=True).stdout
        needed = [l for l in dyn.splitlines() if "NEEDED" in l]
        assert any("libglib-2.0.so.0" in l for l in needed), \
            "liblqr-1.so does not declare NEEDED libglib-2.0.so.0; actual dynamic section: " + dyn
        assert any("libc.so" in l for l in needed), \
            "liblqr-1.so does not declare NEEDED libc.so (OHOS musl)"
        self.output.info("[ok] NEEDED libs: " + ", ".join(
            l.split("[")[1].rstrip("]") for l in needed))

        # RPATH/RUNPATH: the packaged lib must not hardcode build-tree
        # paths; loader resolution goes through conanrun env (LD_LIBRARY_PATH).
        rpaths = [l for l in dyn.splitlines() if "(RPATH)" in l or "(RUNPATH)" in l]
        for l in rpaths:
            assert "conan2" not in l, "leaked conan cache path in RPATH: " + l
            assert "tmp" not in l, "leaked build path in RPATH: " + l
        self.output.info("[ok] no leaked RPATH/RUNPATH entries (%d present)" % len(rpaths))

        # SONAME: libtool 0.3.2 -> soname liblqr-1.so.0
        assert "(SONAME)" in dyn and "liblqr-1.so.0" in dyn, "SONAME liblqr-1.so.0 missing"
        self.output.info("[ok] SONAME liblqr-1.so.0 present")

        # The test binary itself must resolve the library at runtime via
        # conanrun (LD_LIBRARY_PATH), i.e. it really ran against the
        # packaged .so — already proven by the self.run() above.
        bin_dyn = subprocess.run([readelf, "-d", exe], capture_output=True, text=True, check=True).stdout
        assert any("liblqr-1.so.0" in l for l in bin_dyn.splitlines() if "(NEEDED)" in l), \
            "test binary does not link liblqr-1.so.0"
        self.output.info("[ok] test binary NEEDED liblqr-1.so.0 (dynamic resolution via conanrun)")
