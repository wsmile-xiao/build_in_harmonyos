#!/usr/bin/env python3
"""Conan recipe for bibtex 0.99e (TeX Live web2c).

bibtex is a bibliography processor that reads .aux files produced by LaTeX,
reads .bib bibliography databases and .bst style files, and produces .bbl
output for LaTeX.

This recipe builds bibtex from the TeX Live source tree, which includes
both the bibtex WEB source and the kpathsea library it depends on.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class BibtexConan(ConanFile):
    name = "bibtex"
    version = "0.99e"
    description = "BibTeX bibliography processor from TeX Live web2c"
    license = "Knuth License (public domain)"
    homepage = "https://tug.org/bibtex"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    # R32: settings.os 判断用 in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Use Conan generators to set compiler environment
        # VirtualBuildEnv: exports profile [buildenv] (PATH, CONFIG_SHELL, SHELL)
        # AutotoolsToolchain: sets CC/CXX/CFLAGS from profile [conf] tools.build:compiler_executables
        # No os.environ assignments for compiler flags (R33 compliance)
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # Patches are applied via apply_conandata_patches (from conandata.yml):
        #   0001-build-aux-config.guess.patch - HarmonyOS platform detection
        #   0002-configure-mktemp-fix.patch  - HMDFS mktemp -d workaround
        apply_conandata_patches(self)
        src = self.source_folder
        prefix = os.path.join(self.build_folder, "install")

        # R15: No --build/--host flags. config.guess patch handles OHOS detection.
        # R33: Compiler env from AutotoolsToolchain (generated in generate())
        # R6: No runtime modification of config.status/Makefile/libtool.
        #     mktemp issue fixed via configure patch (0002).

        # --- Step 1: Build kpathsea (in-tree) ---
        kp_dir = os.path.join(src, "texk", "kpathsea")
        self.run(f"./configure --prefix={prefix}", cwd=kp_dir)
        self.run("bash config.status", cwd=kp_dir)
        self.run("make -j2", cwd=kp_dir)
        self.run("make install", cwd=kp_dir)

        # --- Step 2: Configure web2c ---
        w2c_dir = os.path.join(src, "texk", "web2c")
        self.run(
            f"./configure --prefix={prefix} --no-create "
            f"--without-x --disable-tex --disable-mf "
            f"--disable-mf-nowin --disable-aleph --disable-hitex "
            f"--disable-pdftex --disable-luatex --disable-texprof "
            f"--disable-xetex --disable-mflua --disable-mfluajit "
            f"--disable-euptex --disable-uptex --disable-etex "
            f"--disable-ipc --disable-dump-share",
            cwd=w2c_dir
        )
        self.run("bash config.status", cwd=w2c_dir)

        # --- Step 3: Configure web2c/web2c subdirectory ---
        w2c_tools = os.path.join(w2c_dir, "web2c")
        self.run(f"./configure --prefix={prefix} --no-create", cwd=w2c_tools)
        self.run("bash config.status", cwd=w2c_tools)

        # --- Step 4: Build lib first, then bibtex ---
        self.run("make", cwd=os.path.join(w2c_dir, "lib"))
        self.run("make bibtex", cwd=w2c_dir)

        # --- Step 5: Copy bibtex binary ---
        bin_dir = os.path.join(prefix, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        bibtex_bin = os.path.join(w2c_dir, ".libs", "bibtex")
        if not os.path.exists(bibtex_bin):
            bibtex_bin = os.path.join(w2c_dir, "bibtex")
        shutil.copy2(bibtex_bin, os.path.join(bin_dir, "bibtex"))

    def package(self):
        prefix = os.path.join(self.build_folder, "install")
        bin_src = os.path.join(prefix, "bin", "bibtex")
        if os.path.exists(bin_src):
            bin_dst = os.path.join(self.package_folder, "bin")
            os.makedirs(bin_dst, exist_ok=True)
            shutil.copy2(bin_src, os.path.join(bin_dst, "bibtex"))

    def package_info(self):
        # R38: Command-line tool - declare bindirs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
