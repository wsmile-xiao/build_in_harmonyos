#!/usr/bin/env python3
"""Conan recipe — afl 1.35b (classic American Fuzzy Lop, Makefile-based fuzzer)."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AflConan(ConanFile):
    name = "afl"
    version = "1.35b"
    description = (
        "American Fuzzy Lop (afl) is a security-oriented fuzzer that uses "
        "compile-time instrumentation and genetic algorithms to find edge "
        "cases in target programs."
    )
    license = "Apache-2.0"
    homepage = "http://lcamtuf.coredump.cx/afl/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # Upstream Makefile PROGS (6 binaries).
    PROGS = [
        "afl-gcc", "afl-as", "afl-fuzz",
        "afl-showmap", "afl-tmin", "afl-gotcpu",
    ]
    # Helper shell scripts shipped in the source root.
    SCRIPTS = ["afl-plot", "afl-cmin", "afl-whatsup"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # afl builds in-source (single Makefile, no configure).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compilers come from the Conan toolchain, never bare shell env.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")

        # Build the 6 binaries as individual targets. The upstream `all`
        # target is avoided on purpose: it chains test_x86 (x86 inline-asm
        # probe, patched to be non-fatal by 0001) and test_build (an
        # instrumentation smoke test) — classic afl's afl-as assembly
        # injection is x86-only and cannot instrument aarch64 binaries
        # (see notes.md for the platform limitation statement).
        self.run(
            "make -j2 {} CC='{}'".format(" ".join(self.PROGS), cc)
        )

    def package(self):
        # Mirror the upstream install layout:
        #   bin/       -> afl-gcc, tools, scripts + afl-g++/afl-clang/afl-clang++
        #   lib/afl/   -> afl-as + `as` symlink (AFL_PATH)
        #   share/afl/ -> testcases/ (fuzzing seeds)
        #   share/doc/afl/ -> docs/
        dst_bin = os.path.join(self.package_folder, "bin")
        dst_helper = os.path.join(self.package_folder, "lib", "afl")
        dst_share = os.path.join(self.package_folder, "share", "afl")
        dst_doc = os.path.join(self.package_folder, "share", "doc", "afl")

        for d in (dst_bin, dst_helper, dst_share, dst_doc):
            os.makedirs(d, exist_ok=True)

        # Binaries.
        for p in self.PROGS:
            src = os.path.join(self.source_folder, p)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_bin, p))
                os.chmod(os.path.join(dst_bin, p), 0o755)

        # Helper scripts.
        for s in self.SCRIPTS:
            src = os.path.join(self.source_folder, s)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_bin, s))
                os.chmod(os.path.join(dst_bin, s), 0o755)

        # afl-as lives in lib/afl (HELPER_PATH) with an `as` symlink;
        # afl-gcc's find_as() locates it via AFL_PATH first (see afl-gcc.c).
        shutil.copy2(
            os.path.join(self.source_folder, "afl-as"),
            os.path.join(dst_helper, "afl-as"),
        )
        os.chmod(os.path.join(dst_helper, "afl-as"), 0o755)
        as_link = os.path.join(dst_helper, "as")
        if not os.path.lexists(as_link):
            os.symlink("afl-as", as_link)

        # afl-gcc dispatch symlinks (created by the Makefile at build time
        # too, but the package must own its copies).
        for s in ("afl-g++", "afl-clang", "afl-clang++"):
            link = os.path.join(dst_bin, s)
            if not os.path.lexists(link):
                os.symlink("afl-gcc", link)

        # Testcases (fuzzing seeds).
        src_tc = os.path.join(self.source_folder, "testcases")
        if os.path.isdir(src_tc):
            shutil.copytree(src_tc, os.path.join(dst_share, "testcases"))

        # Documentation. README is a symlink to docs/README in the tarball.
        docs_src = os.path.join(self.source_folder, "docs")
        if os.path.isdir(docs_src):
            for f in os.listdir(docs_src):
                fp = os.path.join(docs_src, f)
                if os.path.isfile(fp):
                    shutil.copy2(fp, os.path.join(dst_doc, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        # afl-gcc/afl-as locate the assembler wrapper via AFL_PATH.
        self.runenv_info.define(
            "AFL_PATH", os.path.join(self.package_folder, "lib", "afl")
        )
