#!/usr/bin/env python3
"""Conan recipe for genht 1.1.3 — HarmonyOS PC (aarch64-linux-ohos).

genht is a type-generic hash table library written in C (open addressing with
space doubling; type genericity comes from name-prefixing macros).  It ships a
hand written recursive Makefile with **no configure step**, so every knob is a
make variable:

  GENHT_CFLAGS   extra compiler flags appended after the built-in "-g"
  GENHT_LDFLAGS  linker flags used for the sample binary and for libgenht.so
  CC / HOSTCC    target compiler / builder of the tiny ver_edit helper
  PREFIX/DESTDIR install roots (INCDIR=$(install_root)$(DESTDIR)$(PREFIX)/include/genht)

Adaptation notes
----------------
* Source tarball: upstream lives at http://www.repo.hu/projects/genht/releases/
  which serves plain HTTP only (no TLS listener on :443).  The Debian pool copy
  `genht_1.1.3.orig.tar.bz2` is the byte-identical pristine upstream tarball —
  its SHA256 matches the value recorded in FreeBSD ports' distinfo
  (devel/genht: 9861a35c30b5d0023c5f50fa8bb44c3e1df15c232de155888faa492f71f3b1cc)
  — so it is used here to satisfy the https source requirement.
* No build-system patch is required.  The shared object is linked with GNU
  style "-dynamic -rdynamic", which the OHOS flavour of lld accepts; the only
  addition is `-Wl,-soname` so the produced ELF carries DT_SONAME (CMake has no
  HarmonyOS platform module and would otherwise emit a library without one).
* Upstream's single regression target (`make test` → ./mainsi vs mainsi.ref) is
  executed inside build() because OHOS cross-built ELF binaries are executable
  on this worker; a failing diff aborts the build through make's exit status.
* include/ layout follows upstream: headers are installed under include/genht/.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.layout import basic_layout


class GenhtConan(ConanFile):
    name = "genht"
    version = "1.1.3"
    description = "Simple generic hash table implementation in C"
    license = "Public Domain"
    homepage = "http://www.repo.hu/projects/genht"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Leaf package: libc is the only runtime dependency.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ──────────────────────────────────────────────────────────
    def _run_step(self, cmd, log_name):
        """Run a build step with stdout/stderr bound to a real log file.

        Inheriting the parent's output streams makes the OHOS clang driver fail
        silently (log shows "Error 1" but no diagnostic line); redirecting to a
        file keeps every diagnostic and lets us echo the tail afterwards.
        """
        log_path = os.path.join(self.build_folder, log_name)
        self.run(f'{cmd} > "{log_path}" 2>&1')
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
        except OSError:
            return ""
        tail = "\n".join(content.strip().splitlines()[-12:])
        self.output.info(f"--- tail of {log_name} ---\n{tail}\n--- end ---")
        return content

    def _compiler(self):
        """Target compiler: from the profile conf, never from shell env (R33)."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c")
        if compiler:
            return compiler
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "cross builds require tools.build:compiler_executables[c]"
            )
        return "cc"

    def _make_base(self):
        cc = self._compiler()
        cflags = "-O2" if self.settings.build_type != "Debug" else "-O0 -g"
        # Keep the library file name stable (libgenht.so) so that the DT_SONAME
        # recorded in the ELF matches the artefact shipped inside the package.
        ldflags = "-Wl,-soname,libgenht.so"
        src = os.path.join(self.source_folder, "src")
        return (f"make -C {src} -j1 CC={cc} HOSTCC={cc} "
                f"GENHT_CFLAGS='{cflags}' GENHT_LDFLAGS='{ldflags}'"), src

    # ── build ────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        base, _src = self._make_base()

        self._run_step(f"{base} version.h", "version.log")
        self._run_step(f"{base} all", "build.log")

        # Upstream regression test: build ./mainsi, run it and diff its output
        # against src/mainsi.ref.  `make test` exits non-zero on any mismatch,
        # so a silent regression cannot slip through.
        self._run_step(f"{base} test", "upstream-test.log")

    # ── package ──────────────────────────────────────────────────────────
    def package(self):
        _base, src = self._make_base()
        self._run_step(
            f"make -C {src} install_ CP=cp PREFIX= "
            f"DESTDIR={self.package_folder}", "install.log")

        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            # Ship a single, unversioned file whose DT_SONAME equals its name.
            os.rename(os.path.join(libdir, "libgenht.so.1.1.3"),
                      os.path.join(libdir, "libgenht.so"))
            rm(self, "*.a", libdir)
        else:
            rm(self, "libgenht.so*", libdir)

    def package_info(self):
        self.cpp_info.libs = ["genht"]
        self.cpp_info.set_property("cmake_file_name", "genht")
        self.cpp_info.set_property("cmake_target_name", "genht::genht")
        # public headers live under include/genht (upstream install layout)
        self.cpp_info.includedirs = ["include"]
