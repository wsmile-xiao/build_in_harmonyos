#!/usr/bin/env python3
"""Conan recipe for cdbfasta 1.00-git20230710.da8f5ba (upstream Makefile build).

cdbfasta/cdbyank are the CDB indexing and retrieval CLI tools for multi-FASTA
files. Upstream ships a plain Makefile (no install target, no test suite), so
the recipe builds with Conan-provided compiler/zlib paths, exercises the real
index/query workflow in build() as the behavioral check, and packages both
binaries into <pkg>/bin.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CdbfastaConan(ConanFile):
    name = "cdbfasta"
    version = "1.00-git20230710.da8f5ba"
    description = "CDB (Constant DataBase) indexing and retrieval tools for FASTA files"
    license = "Unknown"  # upstream declares no license anywhere in the tree (see notes.md)
    homepage = "https://github.com/gpertea/cdbfasta"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ENABLE_COMPRESSION=1 hardwires -lz (zlib record compression).
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # R33: zlib paths come from the Conan graph. The Makefile *appends*
        # its own flags to environment CXXFLAGS/LDFLAGS (+=), so injecting
        # them via the conanbuild env keeps both the graph paths and the
        # upstream flag logic intact.
        zlib = self.dependencies["zlib"]
        zlib_pf = getattr(zlib, "package_folder", None) or ""

        def _abs(paths):
            return [p if (os.path.isabs(p) or not zlib_pf) else os.path.join(zlib_pf, p) for p in paths]

        incs = _abs(zlib.cpp_info.includedirs)
        libs = _abs(zlib.cpp_info.libdirs)
        self.buildenv_info.define(
            "CXXFLAGS", " ".join("-I{}".format(i) for i in incs)
        )
        self.buildenv_info.define(
            "LDFLAGS", " ".join("-L{}".format(l) for l in libs)
        )

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # Upstream Makefile honours CXX via ?= and has no install target.
        self.run('make -j1 CXX="{}"'.format(cxx), env="conanbuild")
        if can_run(self):
            self._behavior_check()
        else:
            self.output.info(
                "Skipping tool behavior check: target binaries cannot run here"
            )

    def _behavior_check(self):
        """R51: upstream ships no automated test suite (perltest.pl is a usage
        example); exercise the documented index/query workflow instead."""
        fasta = ">s1 description one\nACGTACGTAC\n>s2 description two\nTTTTGGGGCC\n"
        with open("t.fa", "w") as f:
            f.write(fasta)
        self.run('./cdbfasta t.fa', env="conanbuild")
        if not os.path.exists("t.fa.cidx"):
            raise ConanInvalidConfiguration("cdbfasta did not create t.fa.cidx")
        self.output.info("  [ok] cdbfasta created the .cidx index")
        self.run('./cdbyank -a s1 t.fa.cidx > s1.out', env="conanbuild")
        with open("s1.out") as f:
            out1 = f.read()
        if "ACGTACGTAC" not in out1 or "s1" not in out1:
            raise ConanInvalidConfiguration(
                "cdbyank retrieval of s1 lost content: {!r}".format(out1[:120])
            )
        self.output.info("  [ok] cdbyank retrieved full s1 record by key")
        self.run('./cdbyank -a s2 t.fa.cidx > s2.out', env="conanbuild")
        with open("s2.out") as f:
            out2 = f.read()
        if "TTTTGGGGCC" not in out2:
            raise ConanInvalidConfiguration(
                "cdbyank retrieval of s2 lost content: {!r}".format(out2[:120])
            )
        self.output.info("  [ok] cdbyank retrieved full s2 record by key")

    def package(self):
        # No upstream install target: auditable manual packaging of the two
        # tools (abduco family precedent for plain-Makefile CLI tools).
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "cdbfasta", src=self.build_folder, dst=bindir)
        copy(self, "cdbyank", src=self.build_folder, dst=bindir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
