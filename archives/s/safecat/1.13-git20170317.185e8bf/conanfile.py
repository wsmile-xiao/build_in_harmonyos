#!/usr/bin/env python3
"""Conan recipe for safecat 1.13-git20170317.185e8bf."""
import os
from conan import ConanFile
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class SafecatConan(ConanFile):
    name = "safecat"
    version = "1.13-git20170317.185e8bf"
    license = "BSD-3-Clause"
    homepage = "https://github.com/aperezdc/safecat"
    description = "Reliable maildir/spool writer"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # LLVM lld diagnoses two objects listed both directly and inside str.a.
        makefile = os.path.join(self.source_folder, "Makefile")
        text = open(makefile, encoding="utf-8").read()
        block_start = text.index("safecat:")
        block_end = text.index("safecat.0:", block_start)
        block = text[block_start:block_end]
        block = block.replace("byte_copy.o ", "").replace("str_len.o ", "")
        save(self, makefile, text[:block_start] + block + text[block_end:])
        # HMDFS rejects hard links for HiShell users. Preserve the atomic
        # same-filesystem commit with rename() when link() is unavailable.
        source = os.path.join(self.source_folder, "safecat.c")
        code = open(source, encoding="utf-8").read()
        old_commit = """  if(link(tmppath.s,dstpath.s) == -1) {
    unlink(tmppath.s);
    strerr_die2sys(111,"safecat: fatal: ","can't link output file: \ ");
  }
""".replace("output file: \ ", "output file: ")
        new_commit = """  if(link(tmppath.s,dstpath.s) == -1) {
    if ((errno == EPERM || errno == EOPNOTSUPP) && rename(tmppath.s,dstpath.s) == 0) {
      /* HMDFS does not expose hard links; rename is atomic on this filesystem. */
    } else {
      unlink(tmppath.s);
      strerr_die2sys(111,"safecat: fatal: ","can't link output file: ");
    }
  }
"""
        if old_commit not in code:
            raise RuntimeError("safecat link block not found")
        save(self, source, code.replace(old_commit, new_commit, 1))

    def build(self):
        # The upstream djb-style makefiles read these two files directly.
        # Keep the compiler choice in the Conan recipe for OHOS and CI.
        save(self, os.path.join(self.source_folder, "conf-cc"), "clang -O2")
        save(self, os.path.join(self.source_folder, "conf-ld"), "clang")
        self.run("make -j1 safecat maildir", cwd=self.source_folder)

    def package(self):
        copy(self, "safecat", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "maildir", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "safecat.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "maildir.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
