#!/usr/bin/env python3
"""Conan recipe - GNU fontutils 0.7 (2000-era autotools CLI tool suite).

Exploration findings (device, 2026-09-15) baked into this recipe:
- ancient config.guess/config.sub -> build() overwrites them with the
  automake toolchain package copies (E007; keeps the whole-file helpers
  out of the PR diff)
- HMDFS forbids make jobserver FIFOs -> make -j1
- no coreutils `install` on OHOS -> compat/install shim, passed as INSTALL=
- X11 parts (xbfe, lib xmessage.o) are patched out; the remaining tools are
  pure CLI programs that do not install themselves -> package() copies them.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# tools shipped by fontutils 0.7 (xbfe dropped: requires X11)
PROGRAMS = ["bpltobzr", "bzrto", "charspace", "fontconvert", "gsrenderfont",
            "imageto", "imgrotate", "limn"]


class FontutilsConan(ConanFile):
    name = "fontutils"
    version = "0.7"
    description = "GNU font utilities - conversion and manipulation tools for bitmap and scalable font data"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/fontutils/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def build_requirements(self):
        # E007: the config.guess/config.sub copies shipped by this package
        # recognise the ohos triplet, so build() can drop them in instead of
        # carrying the whole-file helpers in compat/ (keeps the PR diff small).
        self.tool_requires("automake/1.18")

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "compat/*", self.recipe_folder,
             os.path.join(self.export_folder, "compat"))

    def layout(self):
        # in-tree build: the 2000 GNUmakefile does `cd subdir && make`,
        # which only works when the build tree mirrors the source tree.
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # compat/install shim is shipped in-tree (no coreutils install on OHOS)
        compat_src = os.path.join(self.recipe_folder, "compat")
        copy(self, "*", compat_src, self.source_folder)
        for f in ("config.guess", "config.sub", os.path.join("compat", "install")):
            path = os.path.join(self.source_folder, f)
            if os.path.exists(path):
                os.chmod(path, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify OHOS; pass triplets explicitly
        # (same approach as argp-standalone).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # widgets Makefile builds -I..$(top_srcdir)/include: top_srcdir must stay relative
        tc.configure_args.append("--srcdir=.")
        tc.generate()

    def _install_config_helpers(self):
        """E007: overwrite the bundled root config.guess/config.sub with the
        automake copies (whole-file content stays out of the PR diff)."""
        base = self.dependencies.build["automake"].package_folder
        for helper in ("config.guess", "config.sub"):
            matches = glob.glob(os.path.join(base, "**", helper), recursive=True)
            if not matches:
                raise ConanInvalidConfiguration(
                    "automake package does not ship %s" % helper)
            dst = os.path.join(self.source_folder, helper)
            shutil.copy2(sorted(matches, key=len)[0], dst)
            os.chmod(dst, 0o755)

    def build(self):
        self._install_config_helpers()
        apply_conandata_patches(self)
        # the tarball ships stale M.depend files referencing //usr/include
        # paths; defs.make regenerates them with  on demand.
        for dep in glob.glob(os.path.join(self.source_folder, "*", "M.depend")):
            os.remove(dep)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS jobserver FIFO creation is not permitted.
        autotools.make(args=["-j1"])

    def package(self):
        # the package's own `make install` only covers data files; the
        # programs have no install rules -> copy them explicitly.
        # `prefix=` overrides the toolchain's empty default at install time;
        # all sub-dirs (datadir etc.) expand recursively from it.
        autotools = Autotools(self)
        install_shim = os.path.join(self.source_folder, "compat", "install")
        autotools.install(args=["prefix=%s" % self.package_folder,
                                "INSTALL=%s" % install_shim])
        for prog in PROGRAMS:
            src = os.path.join(self.build_folder, prog, prog)
            if not os.path.exists(src):
                src = os.path.join(self.source_folder, prog, prog)
            copy(self, prog, os.path.dirname(src),
                 os.path.join(self.package_folder, "bin"))
        # ship the reusable utility library for consumers (lib.a renamed)
        liba = os.path.join(self.source_folder, "lib", "lib.a")
        if os.path.exists(liba):
            libdir = os.path.join(self.package_folder, "lib")
            os.makedirs(libdir, exist_ok=True)
            shutil.copyfile(liba, os.path.join(libdir, "libfontutils.a"))
        data_src = os.path.join(self.build_folder, "data")
        for f in ("*.enc", "*.map", "*.cmi"):
            copy(self, f, data_src,
                 os.path.join(self.package_folder, "share", "fontutil"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["fontutils"]
